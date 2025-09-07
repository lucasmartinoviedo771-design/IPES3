import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from academia_core.models import Carrera, PlanEstudios

logger = logging.getLogger(__name__)


# ======== PANTALLA ========
@login_required
@require_GET
def cargar_carrera_view(request):
    planes = PlanEstudios.objects.all().order_by("resolucion")
    return render(request, "academia_core/cargar_carrera.html", {"planes": planes})


# ======== APIS ========
@login_required
@require_GET
def carrera_list_api(request):
    """Lista de carreras + su plan vigente (si lo hubiera)."""
    items = []
    for c in Carrera.objects.order_by("id"):
        plan_vig = PlanEstudios.objects.filter(carrera=c, vigente=True).first()
        items.append(
            {
                "id": c.id,
                "nombre": str(c),
                "plan_id": plan_vig.id if plan_vig else None,
                "plan_txt": str(plan_vig) if plan_vig else "",
            }
        )
    # Devolvemos lista directamente (lo espera el JS del panel)
    return JsonResponse(items, safe=False)


@login_required
@require_GET
def carrera_get_api(request, pk):
    """Detalle de una carrera + su plan vigente."""
    c = get_object_or_404(Carrera, pk=pk)
    plan_vig = PlanEstudios.objects.filter(carrera=c, vigente=True).first()
    return JsonResponse(
        {
            "id": c.id,
            "nombre": str(c),
            "plan_id": plan_vig.id if plan_vig else None,
        }
    )


@login_required
@require_POST
@transaction.atomic
def carrera_save_api(request):
    """
    Crea/edita Carrera (campo nombre) y, si viene plan_id, marca
    ese plan como vigente para esa carrera (desmarcando los demás).
    """
    data = json.loads(request.body.decode("utf-8"))
    cid = data.get("id")
    nombre = (data.get("nombre") or "").strip()
    plan_id = data.get("plan_id")

    if not nombre:
        return JsonResponse({"ok": False, "error": "Falta el nombre."}, status=400)

    if cid:
        carrera = get_object_or_404(Carrera, pk=cid)
        carrera.nombre = nombre
        carrera.save(update_fields=["nombre"])
    else:
        carrera = Carrera.objects.create(nombre=nombre)

    if plan_id:
        plan = get_object_or_404(PlanEstudios, pk=plan_id)
        # Validamos pertenencia del plan a la carrera
        if plan.carrera_id != carrera.id:
            return JsonResponse(
                {"ok": False, "error": "El plan no pertenece a esa carrera."},
                status=400,
            )
        # Dejamos un único plan vigente por carrera
        PlanEstudios.objects.filter(carrera=carrera, vigente=True).update(vigente=False)
        plan.vigente = True
        plan.save(update_fields=["vigente"])

    return JsonResponse({"ok": True, "id": carrera.id})


@login_required
@require_http_methods(["DELETE"])
@transaction.atomic
@csrf_exempt  # Nota: en producción, conviene manejar CSRF de forma más estricta.
def carrera_delete_api(request, pk):
    c = get_object_or_404(Carrera, pk=pk)
    c.delete()
    return JsonResponse({"ok": True})


@login_required
@require_GET
def plan_list_api(request):
    """Devuelve todos los planes o filtra por carrera (?carrera_id=...)."""
    carrera_id = request.GET.get("carrera_id")
    qs = PlanEstudios.objects.all()
    if carrera_id:
        qs = qs.filter(carrera_id=carrera_id)
    planes = list(qs.values("id", "resolucion").order_by("resolucion"))
    return JsonResponse(planes, safe=False)


@login_required
@require_POST
@csrf_exempt
def plan_save_api(request):
    """
    Crea (o recupera) un PlanEstudios por 'resolucion'.
    Opcionalmente, podrías extender para recibir carrera_id y setear plan.carrera.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
        resol = (data.get("resolucion") or "").strip()
        if not resol:
            return JsonResponse({"ok": False, "error": "Resolución obligatoria"}, status=400)
        plan, _ = PlanEstudios.objects.get_or_create(resolucion=resol)
        return JsonResponse({"ok": True, "id": plan.id})
    except Exception:
        logger.exception("plan_save_api failed")
        return JsonResponse({"ok": False, "error": "Internal server error"}, status=500)
