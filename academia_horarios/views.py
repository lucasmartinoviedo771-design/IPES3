from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import DetailView

from academia_core.models import Carrera
from academia_horarios.forms import DocenteAsignacionForm, HorarioInlineForm
from academia_horarios.models import (
    Catedra,
    Comision,
    DocenteAsignacion,
    HorarioClase,
    Periodo,
    TurnoModel,
)
from ui.api import api_materias_por_plan, api_planes_por_carrera


# ========== UI ==========
@login_required
def cargar_horario(request):
    """Render del template con el layout del panel."""
    ctx = {
        "carreras": Carrera.objects.order_by("nombre"),
        "periodos": Periodo.objects.all().order_by("-ciclo_lectivo", "-cuatrimestre"),
        "turnos": [
            {"id": "maniana", "label": "Mañana"},
            {"id": "tarde", "label": "Tarde"},
            {"id": "noche", "label": "Noche"},
        ],
    }
    return render(request, "academia_horarios/cargar_horario.html", ctx)


# ========== API de grilla (time-slots por turno) ==========
@login_required
@require_GET
def api_timeslots(request):
    """
    GET /panel/horarios/api/timeslots?turno=maniana|tarde|noche
    -> 200 JSON:
       {
         "lv":  [{"orden":..,"ini":..,"fin":..,"recreo":..}, ...],
         "sab": [{"orden":..,"ini":..,"fin":..,"recreo":..}, ...]
       }
    """
    turno = (request.GET.get("turno") or "").lower()

    # Acá devolvemos "constantes" (pueden venir de tu modelo TimeSlot si querés)
    MAPA = {
        "maniana": dict(
            lv=[
                (1, "07:45", "08:25", False),
                (2, "08:25", "09:05", False),
                (3, "09:05", "09:15", True),  # recreo
                (4, "09:15", "09:55", False),
                (5, "09:55", "10:35", False),
                (6, "10:35", "10:45", True),  # recreo
                (7, "10:45", "11:25", False),
                (8, "11:25", "12:05", False),
                (9, "12:05", "12:45", False),
            ],
            sab=[
                (1, "09:00", "09:40", False),
                (2, "09:40", "10:20", False),
                (3, "10:20", "10:30", True),
                (4, "10:30", "11:10", False),
                (5, "11:10", "11:50", False),
                (6, "11:50", "12:00", True),
                (7, "12:00", "12:40", False),
                (8, "12:40", "13:20", False),
                (9, "13:20", "14:00", False),
            ],
        ),
        "tarde": dict(
            lv=[
                (1, "13:00", "13:40", False),
                (2, "13:40", "14:20", False),
                (3, "14:20", "14:30", True),
                (4, "14:30", "15:10", False),
                (5, "15:10", "15:50", False),
                (6, "15:50", "16:00", True),
                (7, "16:00", "16:40", False),
                (8, "16:40", "17:20", False),
                (9, "17:20", "18:00", False),
            ],
            sab=[],  # si no hay, devolvés []
        ),
        "noche": dict(
            lv=[
                (1, "18:10", "18:50", False),
                (2, "18:50", "19:30", False),
                (3, "19:30", "19:40", True),
                (4, "19:40", "20:20", False),
                (5, "20:20", "21:00", False),
                (6, "21:00", "21:10", True),
                (7, "21:10", "21:50", False),
                (8, "21:50", "22:30", False),
                (9, "22:30", "23:10", False),
            ],
            sab=[],
        ),
    }

    cfg = MAPA.get(turno) or MAPA["maniana"]

    def mk(items):
        return [{"orden": o, "ini": a, "fin": b, "recreo": r} for (o, a, b, r) in items]

    return JsonResponse({"lv": mk(cfg["lv"]), "sab": mk(cfg["sab"])}, safe=False)


# ========== Guardar grilla ==========
@login_required
@require_POST
def api_guardar(request):
    """
    POST /panel/horarios/api/guardar/
    Content-Type: application/json

    Request body (ejemplo):
    {
      "plan_id": 123,
      "espacio_id": 456,    // id de EspacioCurricular
      "turno": "maniana",   // o 'tarde' / 'noche'
      "seleccion": {
        "Lun": [1,2,4],     // órdenes de slots L-V
        "Mar": [],
        "Mie": [7],
        "Jue": [],
        "Vie": [],
        "Sab": [4,5]        // órdenes de slots de Sábado
      }
    }

    Respuesta:
      200 {"ok": true}
      400 {"ok": false, "error": "..."}
    """
    import json

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    plan_id = payload.get("plan_id")
    espacio_id = payload.get("espacio_id")
    turno = (payload.get("turno") or "").lower()
    payload.get("seleccion") or {}

    if not plan_id or not espacio_id or not turno:
        return HttpResponseBadRequest("Faltan campos requeridos")

    # >>> Acá va tu lógica real de guardado <<<
    # - Validar que espacio_id pertenece a plan_id (EspacioCurricular.plan_id == plan_id)
    # - Mapear cada orden de slot (por día) a tu modelo real (TimeSlot, HorarioClase, Periodo…)
    # - Crear/actualizar/borrar los registros que correspondan para esa cátedra.
    #
    # Ejemplo de "no-op" (sólo para mostrar que el contrato funciona):
    return JsonResponse({"ok": True})


class ComisionDetailView(DetailView):
    model = Comision
    template_name = "academia_horarios/comision_detail.html"
    context_object_name = "comision"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        comision = self.get_object()
        ctx["horarios"] = (
            HorarioClase.objects.filter(comision=comision)
            .select_related("timeslot")
            .order_by("timeslot__dia_semana", "timeslot__inicio")
        )

        # Get or create Catedra for this Comision
        turno_model_instance = get_object_or_404(TurnoModel, slug=comision.turno)
        catedra, created = Catedra.objects.get_or_create(
            comision=comision,
            materia_en_plan=comision.materia_en_plan,
            turno=turno_model_instance,
            defaults={"horas_semanales": 0, "permite_solape_interno": False},
        )
        ctx["asignaciones_docentes"] = (
            DocenteAsignacion.objects.filter(catedra=catedra)
            .select_related("docente")
            .order_by("docente__apellido", "docente__nombre")
        )

        ctx["form_horario"] = HorarioInlineForm(initial={"comision": comision.pk})
        ctx["form_asignacion"] = DocenteAsignacionForm(initial={"catedra": catedra.pk})
        return ctx


# --- Compatibilidad para el JS v15 ---
api_planes = api_planes_por_carrera
api_materias = api_materias_por_plan
