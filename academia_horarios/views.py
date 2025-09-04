from django.views.generic import TemplateView, DeleteView, ListView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.db.models import Sum, Value, Q
from django.db.models.functions import Concat
from django.contrib import messages
from academia_core.models import PlanEstudios, Carrera, Aula, EspacioCurricular, Docente, Materia, Profesorado
from .models import MateriaEnPlan, Comision, Periodo, HorarioClase, hc_asignadas, hc_requeridas, TimeSlot, Horario
from .forms import HorarioInlineForm
from datetime import time, datetime, date
from django.http import JsonResponse
import json
from django.db import transaction
from django.views.decorators.http import require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.utils import OperationalError, ProgrammingError
import logging

logger = logging.getLogger(__name__)

# Existing classes and functions (OfertaView, comision_detail, HorarioDeleteView)
class OfertaView(TemplateView):
    template_name = "academia_horarios/oferta_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["profesorados"] = Profesorado.objects.all().order_by("nombre")
        ctx["docentes"] = Docente.objects.all().order_by("apellido", "nombre")
        # No meter 'oferta' aquí: la llena el JS por AJAX
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
                    materia_en_plan=mep, periodo=periodo, nombre=nombre,
                    defaults={"turno": Comision.objects.filter(materia_en_plan=mep, periodo=periodo).first().turno if Comision.objects.filter(materia_en_plan=mep, periodo=periodo).exists() else "manana",}
                )
                if was_created:
                    created += 1
            messages.success(request, f"Comisiones '{nombre}' creadas: {created}")
        return redirect(f"{reverse('panel_oferta')}?plan={request.POST.get('plan')}&anio={request.POST.get('anio')}&periodo={request.POST.get('periodo')}")


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
                return redirect(request.path)  # PRG: evita reenvíos y reseteos
            except Exception as e:
                form.add_error(None, str(e))
        messages.error(request, "Revisá los datos del formulario.")
    else:
        form = HorarioInlineForm(initial={"comision": comision.id})

    # Nueva lógica de topes (adaptada para función-based view)
    horas_tope = comision.horas_catedra_tope
    horas_asignadas = comision.horas_asignadas_en_periodo()
    horas_restantes = comision.horas_restantes_en_periodo()
    bloqueado_por_tope = (horas_tope is not None and horas_restantes == 0)

    return render(
        request,
        "academia_horarios/comision_detail.html",
        {
            "object": comision, # Para compatibilidad con el template que usa {{ object }}
            "comision": comision,
            "horarios": horarios,
            "form": form,
            "horas_tope": horas_tope,
            "horas_asignadas": horas_asignadas,
            "horas_restantes": horas_restantes,
            "bloqueado_por_tope": bloqueado_por_tope,
            "docentes": Docente.objects.order_by("apellido_nombre"),
        }
    )

class HorarioDeleteView(DeleteView):
    template_name = "academia_horarios/confirm_delete.html"
    model = HorarioClase
    def get_success_url(self):
        # 1) si viene "next" del form, usamos eso
        nxt = self.request.POST.get("next") or self.request.GET.get("next")
        if nxt:
            return nxt
        # 2) sino, volvemos al detalle de la comisión
        return reverse("panel_comision", args=[self.object.comision_id])

# New cargar_horario view
from academia_core.models import PlanEstudios, Profesorado, Aula, EspacioCurricular, Docente, Materia
from .models import TurnoModel

@transaction.atomic
def cargar_horario(request):
    selected_carrera_id = None
    selected_plan_id = None
    selected_materia_id = None
    selected_turno_value = None # This will hold the 'value' from the select

    if request.method == 'POST':
        selected_carrera_id = request.POST.get('carrera')
        selected_plan_id    = request.POST.get('plan')
        selected_materia_id = request.POST.get('materia')
        selected_turno_value= request.POST.get('turno')

        # Si no quieres el cartel, borra esta línea:
        messages.success(request, "Operación de guardado simulada exitosamente. (El guardado real se implementará luego)")

        # PRG: redirigimos con el estado para repoblar los selects por GET
        qs = (
            f"?carrera={selected_carrera_id or ''}"
            f"&plan={selected_plan_id or ''}"
            f"&materia={selected_materia_id or ''}"
            f"&turno={selected_turno_value or ''}"
        )
        return redirect(f"{request.path}{qs}")

    # Context common to both GET and POST rendering
    carreras = Profesorado.objects.all().order_by('nombre')
    aulas = Aula.objects.all().order_by('nombre')

    # If it's a GET request, or after a POST, try to get initial values from GET params
    if request.method == 'GET':
        selected_carrera_id = request.GET.get('carrera')
        selected_plan_id = request.GET.get('plan')
        selected_materia_id = request.GET.get('materia')
        selected_turno_value = request.GET.get('turno')

    ctx = {
        'carreras': carreras,
        'aulas': aulas,
        'selected_carrera_id': selected_carrera_id,
        'selected_plan_id': selected_plan_id,
        'selected_materia_id': selected_materia_id,
        'selected_turno_value': selected_turno_value, # Pass this to the template
    }

    return render(request, 'academia_horarios/cargar_horario.html', ctx)

# New abrir_paralela view
@transaction.atomic
def abrir_paralela(request, plan_id, periodo_id):
    # origen: sección A
    origen = Comision.objects.filter(
        materia_en_plan__plan_id=plan_id,
        periodo_id=periodo_id,
        seccion='A'
    ).select_related('materia_en_plan')

    if request.method == 'POST':
        seccion_to = request.POST.get('seccion', 'B')
        copiar_horarios = request.POST.get('copiar_horarios') == '1'
        mantener_docentes = request.POST.get('mantener_docentes') == '1'

        # 1) duplicar estructura comisiones
        for c in origen:
            Comision.objects.get_or_create(
                materia_en_plan=c.materia_en_plan,
                periodo=c.periodo,
                seccion=seccion_to
            )

        # 2) duplicar horarios (si se pidió)
        if copiar_horarios:
            # tomamos horarios de 'A' que referencien esas materias/plan/periodo
            # (ajustá filtros según tu Horario)
            a_horarios = Horario.objects.filter(
                plan_id=plan_id,
                # si tenés un "anio" derivado del Periodo, filtralo aquí
            )
            for h in a_horarios:
                nuevo = Horario(
                    carrera=h.carrera,
                    plan=h.plan,
                    materia=h.materia,
                    docente=h.docente if mantener_docentes else None,
                    aula=h.aula,
                    dia=h.dia,
                    inicio=h.inicio,   # antes: hora_inicio
                    fin=h.fin,         # antes: hora_fin
                    turno=h.turno,
                    observaciones=h.observaciones,
                    # quitar: seccion=...
                )
                try:
                    nuevo.full_clean()
                except ValidationError:
                    # choque (docente/aula): si se pidió mantener, reintento sin docente
                    if mantener_docentes and h.docente_id:
                        nuevo.docente = None
                        nuevo.full_clean()  # si vuelve a fallar, dejará la excepción
                nuevo.save()

        messages.success(request, f'Comisión {seccion_to} creada y duplicada.')
        return redirect('academia_horarios:cargar_horario')  # o a donde prefieras

    return render(request, 'academia_horarios/abrir_paralela.html', {
        'plan_id': plan_id,
        'periodo_id': periodo_id,
    })

# Existing API and helper functions
TURNOS = {
    "m":   (time(7,45),  time(12,45)),
    "t":     (time(13,0),  time(18,0)),
    "v":(time(18,10), time(23,10)),
    "s":    (time(9,0),   time(14,0)),
}

def _norm_dia(v):
    # acepta "1..6" o nombres: lunes..sabado
    nombres = {"lunes":1,"martes":2,"miercoles":3,"miércoles":3,"jueves":4,"viernes":5,"sabado":6,"sábado":6}
    s = str(v).strip().lower()
    if s in nombres: return nombres[s]
    try:
        i = int(s)
        if 1 <= i <= 6: return i
    except (TypeError, ValueError):
        pass
    return None

def _norm_turno(s):
    s = (s or "").strip().lower()
    # quitar acentos
    s = s.replace("ñ","n").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    return s

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

    items = [{"id": t.id, "label": f"{t.get_dia_semana_display()} {t.inicio:%H:%M}–{t.fin:%H:%M}"} for t in qs]
    return JsonResponse({"ok": True, "items": items})

@login_required
@require_GET
def horarios_opciones(request):
    """Opciones para combos (materias y docentes) según plan/profesorado."""
    prof_id = request.GET.get('profesorado') or request.GET.get('carrera')
    plan_id = request.GET.get('plan') or request.GET.get('plan_id')

    mats_qs = EspacioCurricular.objects.all()
    if plan_id:
        mats_qs = mats_qs.filter(plan_id=plan_id)
    elif prof_id:
        mats_qs = mats_qs.filter(plan__profesorado_id=prof_id)

    materias = list(mats_qs.order_by('nombre').values('id','nombre'))
    docentes = list(Docente.objects.order_by('apellido','nombre')
                    .values('id', nombre_corto=Concat('apellido', Value(', '), 'nombre')))

    return JsonResponse({'materias': materias, 'docentes': docentes})

from django.core.exceptions import FieldError

def _norm(s):
    return (s or "").strip().lower()

def _axes_from_db(plan_id, espacio_id, turno):
    """
    Devuelve (dias[], horas[], step) sacados de la BD.
    1) Intenta con los TimeSlot usados por los HorarioClase de {plan,espacio,turno}
    2) Si no hay, usa TODOS los TimeSlot de la BD como base
    3) Si sigue vacío, usa un fallback Lun–Vie 08:00–13:00 cada 60'
    """
    step = 60

    ts_ids_qs = HorarioClase.objects.all()
    if plan_id:
        ts_ids_qs = ts_ids_qs.filter(comision__materia_en_plan__plan__id=plan_id)
    if espacio_id:
        try:
            ts_ids_qs = ts_ids_qs.filter(comision__materia_en_plan__espacio__id=espacio_id)
        except FieldError:
            ts_ids_qs = ts_ids_qs.filter(comision__materia_en_plan__materia__id=espacio_id)
    if turno:
        ts_ids_qs = ts_ids_qs.filter(comision__turno=_norm_turno(turno))
    
    ts_ids_qs = ts_ids_qs.values_list("timeslot_id", flat=True)

    slots_qs = TimeSlot.objects.filter(id__in=ts_ids_qs)
    if not slots_qs.exists():
        slots_qs = TimeSlot.objects.all()

    dias = sorted({s["dia_semana"] for s in slots_qs.values("dia_semana").distinct()})
    horas = sorted({ts.strftime("%H:%M") for ts in slots_qs.values_list("inicio", flat=True).distinct()})

    if not dias or not horas:
        dias  = [1,2,3,4,5]
        horas = [f"{h:02d}:00" for h in range(8,13)]
        step  = 60

    return dias, horas, step

@login_required
@require_GET
def horarios_grilla(request):
    plan_id    = request.GET.get("plan")
    espacio_id = request.GET.get("materia")
    turno      = _norm(request.GET.get("turno"))

    # --- Ejes de tiempo ---
    axes = {}
    try:
        def _tramos(qs):
            out = []
            for s in qs.order_by('inicio'):
                # duración en minutos
                dur = (datetime.combine(date(2000,1,1), s.fin) -
                       datetime.combine(date(2000,1,1), s.inicio)).seconds // 60
                # si existe es_recreo en el modelo úsalo; si no, o si está vacío, infiere por duración
                rec_db = getattr(s, 'es_recreo', None)
                recreo = bool(rec_db) if rec_db is not None else False
                # tolerancia: si el tramo es de ~10' lo consideramos recreo
                if dur <= 12:
                    recreo = True

                out.append({
                    "desde": s.inicio.strftime("%H:%M"),
                    "hasta": s.fin.strftime("%H:%M"),
                    "recreo": recreo,
                })
            return out

        slots = TimeSlot.objects.all()
        # si tu tabla TIENE 'turno' y está poblado, filtrá:
        try:
            if turno:
                slots = slots.filter(turno=turno)
        except Exception:
            pass

        # qué códigos de día existen realmente en BD
        dias_existentes = sorted(set(slots.values_list('dia_semana', flat=True)))

        # el código de sábado puede ser 6 o 7: detectarlo
        sat_code = 6 if 6 in dias_existentes else (7 if 7 in dias_existentes else None)

        # días de lunes a viernes que existan en la BD
        dias_lv = [d for d in dias_existentes if d in (1,2,3,4,5)]
        ref_lv = dias_lv[0] if dias_lv else None  # tomo un día de referencia para L-V

        lv = _tramos(slots.filter(dia_semana=ref_lv)) if ref_lv else []
        sab = _tramos(slots.filter(dia_semana=sat_code)) if sat_code else []

        # si alguno vino vacío y el otro no, igual devolvé arrays del mismo largo
        if not lv and sab:
            lv = [{"desde":"","hasta":"","recreo":False} for _ in range(len(sab))]
        if not sab and lv:
            sab = [{"desde":"","hasta":"","recreo":False} for _ in range(len(lv))]

        # 'dias' para el header (L-V + sábado si existe)
        dias_header = [1,2,3,4,5] + ([sat_code] if sat_code else [])

        axes = {"dias": dias_header, "lv": lv, "sab": sab}
    except (OperationalError, ProgrammingError) as e:
        logger.exception("Axes error: %s", e)
        axes = {"dias": [], "lv": [], "sab": [], "rows": [], "error": "DB error"}
    except Exception as e:
        logger.exception("Unexpected axes error: %s", e)
        axes = {"dias": [], "lv": [], "sab": [], "rows": [], "error": "Unknown error"}

    # --- Filas (bloques cargados) ---
    rows = []
    try:
        qs = (HorarioClase.objects
              .filter(comision__materia_en_plan__plan__id=plan_id)
              .select_related("timeslot","comision","comision__materia_en_plan")
              .prefetch_related("docentes"))
        
        if espacio_id:
            try:
                qs = qs.filter(comision__materia_en_plan__espacio__id=espacio_id)
            except Exception:
                qs = qs.filter(comision__materia_en_plan__materia__id=espacio_id)
        if turno:
            try:
                qs = qs.filter(comision__turno=turno)
            except Exception:
                pass

        for h in qs.order_by("timeslot__dia_semana","timeslot__inicio"):
            t = h.timeslot
            rows.append({
                "id": h.id,
                "dia": t.dia_semana,
                "desde": t.inicio.strftime("%H:%M"),
                "hasta": t.fin.strftime("%H:%M"),
                "comision": getattr(h.comision, "nombre", ""),
                "aula": getattr(getattr(h, "aula", None), "nombre", "") or "",
                "docentes": [getattr(d, "apellido_nombre", str(d))
                             for d in getattr(h, "docentes", []).all()] if hasattr(h, "docentes") else [],
            })
    except (OperationalError, ProgrammingError) as e:
        logger.exception("Rows error: %s", e)
        rows = []
    except Exception as e:
        logger.exception("Unexpected rows error: %s", e)
        rows = []

    axes["rows"] = rows
    return JsonResponse(axes)


from datetime import datetime
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import TimeSlot, HorarioClase, MateriaEnPlan, Comision

def _spec_turno(turno: str):
    turno = (turno or "").lower()
    if turno in ("mañana","manana"):
        lv = [
            {"desde":"07:45","hasta":"08:25","recreo":False},
            {"desde":"08:25","hasta":"09:05","recreo":False},
            {"desde":"09:05","hasta":"09:15","recreo":True },
            {"desde":"09:15","hasta":"09:55","recreo":False},
            {"desde":"09:55","hasta":"10:35","recreo":False},
            {"desde":"10:35","hasta":"10:45","recreo":True },
            {"desde":"10:45","hasta":"11:25","recreo":False},
            {"desde":"11:25","hasta":"12:05","recreo":False},
            {"desde":"12:05","hasta":"12:45","recreo":False},
        ]
        sab = [
            {"desde":"09:00","hasta":"09:40","recreo":False},
            {"desde":"09:40","hasta":"10:20","recreo":False},
            {"desde":"10:20","hasta":"10:30","recreo":True},
            {"desde":"10:30","hasta":"11:10","recreo":False},
            {"desde":"11:10","hasta":"11:50","recreo":False},
            {"desde":"11:50","hasta":"12:00","recreo":True},
            {"desde":"12:00","hasta":"12:40","recreo":False},
            {"desde":"12:40","hasta":"13:20","recreo":False},
            {"desde":"13:20","hasta":"14:00","recreo":False},
        ]
    else:
        lv, sab = [], []
    return lv, sab

def _t(hhmm): return datetime.strptime(hhmm, "%H:%M").time()

@login_required
@require_POST
def horarios_guardar(request):
    try:
        p = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    plan_id   = int(p.get("plan_id") or 0)
    espacio_id = int(p.get("espacio_id") or 0)
    turno     = (p.get("turno") or "").lower()
    keys      = set(p.get("keys") or [])

    if not (plan_id and espacio_id and turno is not None and keys is not None):
        return JsonResponse({"ok": False, "error": "Faltan parámetros"}, status=400)

    try:
        mep = MateriaEnPlan.objects.select_related("plan","espacio").get(
            plan_id=plan_id, espacio_id=espacio_id
        )
    except MateriaEnPlan.DoesNotExist:
        return JsonResponse({"ok": False, "error": "MateriaEnPlan inexistente"}, status=404)

    com_kwargs = {"materia_en_plan": mep}
    if hasattr(Comision, "turno"):
        com_kwargs["turno"] = turno
    comision, _ = Comision.objects.get_or_create(**com_kwargs)

    lv, sab = _spec_turno(turno)
    fin_by_desde = {r["desde"]: r["hasta"] for r in lv if not r["recreo"]}
    fin_by_desde_sab = {r["desde"]: r["hasta"] for r in sab if not r["recreo"]}

    existentes = HorarioClase.objects.filter(comision=comision).select_related("timeslot")
    current = set(f"{hc.timeslot.dia_semana} @{hc.timeslot.inicio.strftime('%H:%M')}" for hc in existentes)

    to_add = keys - current
    to_del = current - keys
    added = removed = 0
    errors = []

    for key in to_add:
        try:
            di_str, hhmm = key.split(" @", 1)
            di = int(di_str)
        except Exception:
            errors.append(f"key inválida: {key}")
            continue

        fin = fin_by_desde.get(hhmm) if di in (1,2,3,4,5) else fin_by_desde_sab.get(hhmm)
        if not fin:
            errors.append(f"sin fin para {key}")
            continue

        ts, _ = TimeSlot.objects.get_or_create(
            turno=turno, dia_semana=di, inicio=_t(hhmm), fin=_t(fin)
        )
        HorarioClase.objects.get_or_create(comision=comision, timeslot=ts)
        added += 1

    if to_del:
        for hc in existentes:
            k = f"{hc.timeslot.dia_semana} @{hc.timeslot.inicio.strftime('%H:%M')}"
            if k in to_del:
                hc.delete()
                removed += 1

    if errors:
        return JsonResponse({"ok": False, "error": ", ".join(errors)}, status=400)

    # Limpiamos la grilla después de guardar
    # para reflejar el estado actual
    loadGrid()

    return JsonResponse({"ok": True, "added": added, "removed": removed, "errors": errors})
