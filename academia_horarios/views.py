from django.views.generic import TemplateView, DeleteView, ListView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.db.models import Sum
from django.contrib import messages
from academia_core.models import PlanEstudios, Carrera, Aula, EspacioCurricular, Docente, Materia # Added Carrera, Aula, EspacioCurricular, Docente, Materia
from .models import MateriaEnPlan, Comision, Periodo, HorarioClase, hc_asignadas, hc_requeridas, TimeSlot, Horario # Added Horario
from .forms import HorarioInlineForm
from datetime import time
from django.http import JsonResponse
import json # Added json
from django.db import transaction # Added transaction
from django.views.decorators.http import require_GET # Already there

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