# academia_horarios/views.py
from __future__ import annotations

import json
import logging
from datetime import time, datetime, date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldError, ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Value
from django.db.models.functions import Concat
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.generic import TemplateView, DeleteView
from django.forms import ModelForm

from academia_core.models import (
    PlanEstudios,
    Carrera,
    Aula,
    EspacioCurricular,   # “Materia en Plan” (tabla puente Plan↔Materia)
    Docente,
    Materia,
    Profesorado as Carrera,  # Using Profesorado as Carrera
)
from .forms import HorarioInlineForm
from .models import (
    MateriaEnPlan,  # alias del mismo concepto de Espacio Curricular si lo usas como modelo propio
    Comision,
    Periodo,
    HorarioClase,
    hc_asignadas,
    hc_requeridas,
    TimeSlot,
    Horario,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Oferta (se conserva para compatibilidad)
# -----------------------------------------------------------------------------
class OfertaView(TemplateView):
    template_name = "academia_horarios/oferta_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["profesorados"] = Carrera.objects.all().order_by("nombre")
        ctx["docentes"] = Docente.objects.all().order_by("apellido", "nombre")
        # 'oferta' la llena el JS por AJAX
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "desdoblar":
            plan_id = request.POST.get("plan")
            anio = request.POST.get("anio")
            periodo_id = request.POST.get("periodo")
            nombre = request.POST.get("nombre", "B").strip() or "B"
            periodo = Periodo.objects.get(pk=periodo_id)
            meps = MateriaEnPlan.objects.filter(plan_id=plan_id, anio=anio)
            created = 0
            for mep in meps:
                obj, was_created = Comision.objects.get_or_create(
                    materia_en_plan=mep,
                    periodo=periodo,
                    nombre=nombre,
                    defaults={
                        "turno": (
                            Comision.objects
                            .filter(materia_en_plan=mep, periodo=periodo)
                            .first().turno
                            if Comision.objects.filter(materia_en_plan=mep, periodo=periodo).exists()
                            else "manana"
                        ),
                    },
                )
                if was_created:
                    created += 1
            messages.success(request, f"Comisiones '{nombre}' creadas: {created}")
        return redirect(
            f"{reverse('panel_oferta')}?plan={request.POST.get('plan')}"
            f"&anio={request.POST.get('anio')}&periodo={request.POST.get('periodo')}"
        )


def comision_detail(request, pk):
    comision = get_object_or_404(Comision, pk=pk)
    horarios = (
        HorarioClase.objects
        .filter(comision=comision)
        .select_related("timeslot")
        .prefetch_related("docentes")
    )

    if request.method == "POST":
        form = HorarioInlineForm(request.POST)
        if form.is_valid():
            try:
                form.save(comision)
                messages.success(request, "Horario agregado.")
                return redirect(request.path)  # PRG
            except Exception as e:
                form.add_error(None, str(e))
        messages.error(request, "Revisá los datos del formulario.")
    else:
        form = HorarioInlineForm(initial={"comision": comision.id})

    horas_tope = comision.horas_catedra_tope
    horas_asignadas = comision.horas_asignadas_en_periodo()
    horas_restantes = comision.horas_restantes_en_periodo()
    bloqueado_por_tope = (horas_tope is not None and horas_restantes == 0)

    return render(
        request,
        "academia_horarios/comision_detail.html",
        {
            "object": comision,  # compat con template existente
            "comision": comision,
            "horarios": horarios,
            "form": form,
            "horas_tope": horas_tope,
            "horas_asignadas": horas_asignadas,
            "horas_restantes": horas_restantes,
            "bloqueado_por_tope": bloqueado_por_tope,
            "docentes": Docente.objects.order_by("apellido_nombre"),
        },
    )


class HorarioDeleteView(DeleteView):
    template_name = "academia_horarios/confirm_delete.html"
    model = HorarioClase

    def get_success_url(self):
        nxt = self.request.POST.get("next") or self.request.GET.get("next")
        if nxt:
            return nxt
        return reverse("panel_comision", args=[self.object.comision_id])


# -----------------------------------------------------------------------------
# Pantalla "Armar Horarios de Cátedra"
# -----------------------------------------------------------------------------
@login_required
def cargar_horario(request):
    """
    Renderiza la pantalla de la grilla. Los combos se llenan por AJAX.
    """
    carreras = Carrera.objects.all().order_by("nombre")
    aulas = Aula.objects.all().order_by("nombre")

    # Recordar selección si vuelve por GET (PRG)
    selected_carrera_id = request.GET.get("carrera")
    selected_plan_id = request.GET.get("plan")
    selected_materia_id = request.GET.get("materia")
    selected_turno_value = request.GET.get("turno")

    ctx = {
        "carreras": carreras,
        "aulas": aulas,
        "selected_carrera_id": selected_carrera_id,
        "selected_plan_id": selected_plan_id,
        "selected_materia_id": selected_materia_id,
        "selected_turno_value": selected_turno_value,
    }
    return render(request, "academia_horarios/cargar_horario.html", ctx)


# Detección de turnos para filtrar TimeSlot en /api/timeslots/
TURNOS = {
    "m": (time(7, 45), time(12, 45)),   # mañana
    "t": (time(13, 0), time(18, 0)),    # tarde
    "v": (time(18, 10), time(23, 10)),  # vespertino
    "s": (time(9, 0), time(14, 0)),     # sábado
}


def _norm_dia(v):
    nombres = {
        "lunes": 1, "martes": 2, "miercoles": 3, "miércoles": 3,
        "jueves": 4, "viernes": 5, "sabado": 6, "sábado": 6
    }
    s = str(v).strip().lower()
    if s in nombres:
        return nombres[s]
    try:
        i = int(s)
        if 1 <= i <= 6:
            return i
    except (TypeError, ValueError):
        pass
    return None


def _norm_turno(s: str) -> str:
    s = (s or "").strip().lower()
    return (
        s.replace("ñ", "n").replace("á", "a").replace("é", "e")
        .replace("í", "i").replace("ó", "o").replace("ú", "u")
    )


@require_GET
def timeslots_api(request):
    dia = _norm_dia(request.GET.get("dia"))
    turno = _norm_turno(request.GET.get("turno"))

    qs = TimeSlot.objects.all()
    if dia:
        qs = qs.filter(dia_semana=dia)

    rango = TURNOS.get(turno)
    if rango:
        desde, hasta = rango
        qs = qs.filter(inicio__gte=desde, fin__lte=hasta)

    qs = qs.order_by("dia_semana", "inicio")
    items = [
        {"id": t.id, "label": f"{t.get_dia_semana_display()} {t.inicio:%H:%M}–{t.fin:%H:%M}"}
        for t in qs
    ]
    return JsonResponse({"ok": True, "items": items})


# -----------------------------------------------------------------------------
# API: combos de Materias + Docentes
# -----------------------------------------------------------------------------
@login_required
@require_GET
def horarios_opciones(request):
    """
    Devuelve opciones para:
      - materias (Espacios curriculares) del plan o del profesorado
      - docentes (lista completa con nombre corto)
    """
    prof_id = request.GET.get("profesorado") or request.GET.get("carrera")
    plan_id = request.GET.get("plan") or request.GET.get("plan_id")

    mats_qs = EspacioCurricular.objects.all()
    if plan_id:
        mats_qs = mats_qs.filter(plan_id=plan_id)
    elif prof_id:
        mats_qs = mats_qs.filter(plan__profesorado_id=prof_id)

    materias = list(
        mats_qs.order_by("nombre").values("id", "nombre")
    )
    docentes = list(
        Docente.objects.order_by("apellido", "nombre")
        .values("id", nombre_corto=Concat("apellido", Value(", "), "nombre"))
    )

    return JsonResponse({"materias": materias, "docentes": docentes})


# -----------------------------------------------------------------------------
# API: grilla (ejes + filas)
# -----------------------------------------------------------------------------
@login_required
@require_GET
def horarios_grilla(request):
    """
    Devuelve formato:
      {
        dias: [1,2,3,4,5,6?],
        lv: [{desde, hasta, recreo}, ...],
        sab: [{desde, hasta, recreo}, ...],
        rows: [
          {id, dia, desde, hasta, comision, aula, docentes:[]}, ...
        ]
      }
    """
    plan_id = request.GET.get("plan")
    espacio_id = request.GET.get("materia")
    turno = _norm_turno(request.GET.get("turno"))

    # ----- Ejes (horarios base) -----
    axes = {}
    try:
        def _tramos(qs):
            out = []
            for s in qs.order_by("inicio"):
                # duración en minutos
                dur = (
                    datetime.combine(date(2000, 1, 1), s.fin)
                    - datetime.combine(date(2000, 1, 1), s.inicio)
                ).seconds // 60
                rec_db = getattr(s, "es_recreo", None)
                recreo = bool(rec_db) if rec_db is not None else (dur <= 12)
                out.append({
                    "desde": s.inicio.strftime("%H:%M"),
                    "hasta": s.fin.strftime("%H:%M"),
                    "recreo": recreo,
                })
            return out

        slots = TimeSlot.objects.all()
        try:
            if turno:
                slots = slots.filter(turno=turno)
        except Exception:
            pass

        dias_existentes = sorted(set(slots.values_list("dia_semana", flat=True)))
        sat_code = 6 if 6 in dias_existentes else (7 if 7 in dias_existentes else None)
        dias_lv = [d for d in dias_existentes if d in (1, 2, 3, 4, 5)]
        ref_lv = dias_lv[0] if dias_lv else None

        lv = _tramos(slots.filter(dia_semana=ref_lv)) if ref_lv else []
        sab = _tramos(slots.filter(dia_semana=sat_code)) if sat_code else []

        if not lv and sab:
            lv = [{"desde": "", "hasta": "", "recreo": False} for _ in range(len(sab))]
        if not sab and lv:
            sab = [{"desde": "", "hasta": "", "recreo": False} for _ in range(len(lv))]

        dias_header = [1, 2, 3, 4, 5] + ([sat_code] if sat_code else [])
        axes = {"dias": dias_header, "lv": lv, "sab": sab}

    except (OperationalError, ProgrammingError) as e:
        logger.exception("Axes error: %s", e)
        axes = {"dias": [], "lv": [], "sab": [], "rows": [], "error": "DB error"}
    except Exception as e:
        logger.exception("Unexpected axes error: %s", e)
        axes = {"dias": [], "lv": [], "sab": [], "rows": [], "error": "Unknown error"}

    # ----- Filas (bloques cargados) -----
    rows = []
    try:
        qs = (
            HorarioClase.objects
            .filter(comision__materia_en_plan__plan__id=plan_id)
            .select_related("timeslot", "comision", "comision__materia_en_plan")
            .prefetch_related("docentes")
        )
        if espacio_id:
            try:
                # En tus modelos la relación correcta es materia_en_plan__materia__id
                qs = qs.filter(comision__materia_en_plan__materia__id=espacio_id)
            except Exception:
                qs = qs.filter(comision__materia_en_plan__materia__id=espacio_id)

        if turno:
            try:
                qs = qs.filter(comision__turno=turno)
            except Exception:
                pass

        for h in qs.order_by("timeslot__dia_semana", "timeslot__inicio"):
            t = h.timeslot
            rows.append({
                "id": h.id,
                "dia": t.dia_semana,
                "desde": t.inicio.strftime("%H:%M"),
                "hasta": t.fin.strftime("%H:%M"),
                "comision": getattr(h.comision, "nombre", ""),
                "aula": getattr(getattr(h, "aula", None), "nombre", "") or "",
                "docentes": [
                    getattr(d, "apellido_nombre", str(d))
                    for d in getattr(h, "docentes", []).all()
                ] if hasattr(h, "docentes") else [],
            })
    except (OperationalError, ProgrammingError) as e:
        logger.exception("Rows error: %s", e)
        rows = []
    except Exception as e:
        logger.exception("Unexpected rows error: %s", e)
        rows = []

    axes["rows"] = rows
    return JsonResponse(axes)


# -----------------------------------------------------------------------------
# API: guardar malla
# -----------------------------------------------------------------------------
def _t(hhmm: str):
    return datetime.strptime(hhmm, "%H:%M").time()


# Catálogo de tramos (mañana/tarde/vespertino + sábado).
# Los recreos están para mantener índice pero no se crean HorarioClase en ellos.
SLOTS = [
    (_t("07:45"), _t("08:25")),  # 0
    (_t("08:25"), _t("09:05")),  # 1
    (_t("09:05"), _t("09:15")),  # 2 (recreo)
    (_t("09:15"), _t("09:55")),  # 3
    (_t("09:55"), _t("10:35")),  # 4
    (_t("10:35"), _t("10:45")),  # 5 (recreo)
    (_t("10:45"), _t("11:25")),  # 6
    (_t("11:25"), _t("12:05")),  # 7
    (_t("12:05"), _t("12:45")),  # 8
    (_t("13:00"), _t("13:40")),  # 9
    (_t("13:40"), _t("14:20")),  # 10
    (_t("14:20"), _t("14:30")),  # 11 (recreo)
    (_t("14:30"), _t("15:10")),  # 12
    (_t("15:10"), _t("15:50")),  # 13
    (_t("15:50"), _t("16:00")),  # 14 (recreo)
    (_t("16:00"), _t("16:40")),  # 15
    (_t("16:40"), _t("17:20")),  # 16
    (_t("17:20"), _t("18:00")),  # 17
    (_t("18:10"), _t("18:50")),  # 18
    (_t("18:50"), _t("19:30")),  # 19
    (_t("19:30"), _t("19:40")),  # 20 (recreo)
    (_t("19:40"), _t("20:20")),  # 21
    (_t("20:20"), _t("21:00")),  # 22
    (_t("21:00"), _t("21:10")),  # 23 (recreo)
    (_t("21:10"), _t("21:50")),  # 24
    (_t("21:50"), _t("22:30")),  # 25
    (_t("22:30"), _t("23:10")),  # 26
    # Sábado
    (_t("09:00"), _t("09:40")),  # 27
    (_t("09:40"), _t("10:20")),  # 28
    (_t("10:20"), _t("10:30")),  # 29 (recreo)
    (_t("10:30"), _t("11:10")),  # 30
    (_t("11:10"), _t("11:50")),  # 31
    (_t("11:50"), _t("12:00")),  # 32 (recreo)
    (_t("12:00"), _t("12:40")),  # 33
    (_t("12:40"), _t("13:20")),  # 34
    (_t("13:20"), _t("14:00")),  # 35
]


def _get_or_create_periodo(turno: str | None = None, periodo_id: int | None = None):
    """
    Devuelve un Periodo válido. Si viene periodo_id => lo usa.
    Si no, intenta tomar uno para el ciclo y cuatrimestre actual.
    Si no existe, crea uno por defecto para el año actual.
    """
    if periodo_id:
        return Periodo.objects.get(pk=periodo_id)

    now = timezone.now()
    current_year = now.year
    current_cuatrimestre = 1 if now.month <= 6 else 2

    periodo, created = Periodo.objects.get_or_create(
        ciclo_lectivo=current_year,
        cuatrimestre=current_cuatrimestre,
    )
    return periodo


@login_required
@require_POST
def horarios_guardar(request):
    """
    Espera JSON:
      {
        plan_id: <int>,
        espacio_id: <int>,     // id de Materia (no del EspacioCurricular)
        turno: "manana"|"tarde"|"vespertino"|"sabado",
        rows: [{d:<1..6>, i:<idx-slot>}, ...]  // sin recreos
      }
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"JSON inválido: {e}"}, status=400)

    plan_id = payload.get("plan_id")
    espacio_id = payload.get("espacio_id")
    turno = payload.get("turno")
    rows = payload.get("rows")
    periodo_id = payload.get("periodo_id")

    if not plan_id or not espacio_id or not turno or rows is None:
        return JsonResponse(
            {"ok": False, "error": "Faltan parámetros (plan_id, espacio_id, turno, rows)."},
            status=400,
        )

    try:
        plan_id = int(plan_id)
        espacio_id = int(espacio_id)
    except ValueError:
        return JsonResponse({"ok": False, "error": "plan_id/espacio_id deben ser enteros."}, status=400)

    # Relación correcta: MateriaEnPlan(plan=plan_id, materia__id=espacio_id)
    try:
        mep = MateriaEnPlan.objects.select_related("plan", "materia").get(
            plan_id=plan_id,
            materia__id=espacio_id,
        )
    except MateriaEnPlan.DoesNotExist:
        return JsonResponse(
            {"ok": False, "error": "Materia/Plan inexistente para ese Plan y Materia."},
            status=404,
        )

    periodo = _get_or_create_periodo(turno=turno, periodo_id=periodo_id)

    com_kwargs = {"materia_en_plan": mep, "periodo": periodo}
    if hasattr(Comision, "turno"):
        com_kwargs["turno"] = (turno or "").lower()
    comision, _ = Comision.objects.get_or_create(**com_kwargs)

    # Horarios actuales
    existentes = (
        HorarioClase.objects
        .filter(comision=comision)
        .select_related("timeslot")
    )
    actuales = {
        f"{hc.timeslot.dia_semana} @{SLOTS.index((hc.timeslot.inicio, hc.timeslot.fin))}": hc
        for hc in existentes
    }

    # Normalizar rows solicitadas
    solicitadas = set()
    for r in rows:
        try:
            dia = int(r["d"])
            idx = int(r["i"])
            if not (0 <= idx < len(SLOTS)):
                raise ValueError(f"Índice de slot fuera de rango: {idx}")
            solicitadas.add(f"{dia} @{idx}")
        except Exception as e:
            return JsonResponse(
                {"ok": False, "error": f"Formato de fila inválido: {r} ({e})"},
                status=400,
            )

    to_add = solicitadas - set(actuales.keys())
    to_del = set(actuales.keys()) - solicitadas

    added = removed = 0
    errors: list[str] = []

    # Conjunto de recreos para no crear entradas
    recreos = {
        (_t("09:05"), _t("09:15")),
        (_t("10:35"), _t("10:45")),
        (_t("19:30"), _t("19:40")),
        (_t("21:00"), _t("21:10")),
        (_t("10:20"), _t("10:30")),
        (_t("11:50"), _t("12:00")),
    }

    try:
        with transaction.atomic():
            # Altas
            for key in to_add:
                try:
                    di_str, idx_str = key.split(" @", 1)
                    dia = int(di_str)
                    idx = int(idx_str)
                    inicio, fin = SLOTS[idx]

                    if (inicio, fin) in recreos:
                        errors.append(f"Tramo no permitido (recreo): {key}")
                        continue

                    ts, _ = TimeSlot.objects.get_or_create(
                        turno=(turno or "").lower(),
                        dia_semana=dia,
                        inicio=inicio,
                        fin=fin,
                    )
                    HorarioClase.objects.get_or_create(comision=comision, timeslot=ts)
                    added += 1
                except Exception as e:
                    errors.append(f"Error al procesar alta para {key}: {e}")
                    continue

            # Bajas
            for key in to_del:
                try:
                    hc_to_delete = actuales[key]
                    hc_to_delete.delete()
                    removed += 1
                except Exception as e:
                    errors.append(f"Error al procesar baja para {key}: {e}")
                    continue

    except IntegrityError as e:
        return JsonResponse({"ok": False, "error": f"Error de integridad: {e}"}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Excepción no controlada: {e}"}, status=500)

    if errors:
        return JsonResponse({"ok": True, "added": added, "removed": removed, "warnings": errors})
    return JsonResponse({"ok": True, "added": added, "removed": removed})


# -----------------------------------------------------------------------------
# Utilidad: abrir paralela (stub/compat)
# -----------------------------------------------------------------------------
@login_required
@transaction.atomic
def abrir_paralela(request, plan_id, periodo_id):
    origen = (
        Comision.objects
        .filter(materia_en_plan__plan_id=plan_id, periodo_id=periodo_id, seccion="A")
        .select_related("materia_en_plan")
    )

    if request.method == "POST":
        seccion_to = request.POST.get("seccion", "B")
        copiar_horarios = request.POST.get("copiar_horarios") == "1"
        mantener_docentes = request.POST.get("mantener_docentes") == "1"

        # 1) duplicar estructura de comisiones
        for c in origen:
            Comision.objects.get_or_create(
                materia_en_plan=c.materia_en_plan,
                periodo=c.periodo,
                seccion=seccion_to,
            )

        # 2) (opcional) duplicar horarios existentes de la paralela A
        if copiar_horarios:
            a_horarios = Horario.objects.filter(plan_id=plan_id)
            for h in a_horarios:
                nuevo = Horario(
                    carrera=h.carrera,
                    plan=h.plan,
                    materia=h.materia,
                    docente=h.docente if mantener_docentes else None,
                    aula=h.aula,
                    dia=h.dia,
                    inicio=h.inicio,
                    fin=h.fin,
                    turno=h.turno,
                    observaciones=h.observaciones,
                )
                try:
                    nuevo.full_clean()
                except ValidationError:
                    if mantener_docentes and h.docente_id:
                        nuevo.docente = None
                        nuevo.full_clean()
                nuevo.save()

        messages.success(request, f"Comisión {seccion_to} creada y duplicada.")
        return redirect("academia_horarios:cargar_horario")

    return render(
        request,
        "academia_horarios/abrir_paralela.html",
        {"plan_id": plan_id, "periodo_id": periodo_id},
    )