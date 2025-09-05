from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db import transaction
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from academia_core.models import Profesorado, PlanEstudios


# ======== PANTALLA ========
@login_required
@require_GET
def cargar_carrera_view(request):
    planes = PlanEstudios.objects.all().order_by('resolucion')
    return render(request, "academia_core/cargar_carrera.html", {'planes': planes})


# ======== APIS ========
@login_required
@require_GET
def carrera_list_api(request):
    items = []
    for c in Profesorado.objects.order_by("id"):
        plan_vig = PlanEstudios.objects.filter(profesorado=c, vigente=True).first()
        items.append({
            "id": c.id,
            "nombre": str(c),
            "plan_id": plan_vig.id if plan_vig else None,
            "plan_txt": str(plan_vig) if plan_vig else "",
        })
    return JsonResponse(items, safe=False) # Return a list directly, as expected by JS


@login_required
@require_GET
def carrera_get_api(request, pk):
    c = get_object_or_404(Profesorado, pk=pk)
    plan_vig = PlanEstudios.objects.filter(profesorado=c, vigente=True).first()
    return JsonResponse({
        "id": c.id,
        "nombre": str(c),
        "plan_id": plan_vig.id if plan_vig else None,
    })


@login_required
@require_POST
@transaction.atomic
def carrera_save_api(request):
    data = json.loads(request.body.decode("utf-8"))
    cid     = data.get("id")
    nombre  = (data.get("nombre") or "").strip()
    plan_id = data.get("plan_id")

    if not nombre:
        return JsonResponse({"ok": False, "error": "Falta el nombre."}, status=400)

    if cid:
        carrera = get_object_or_404(Profesorado, pk=cid)
        if hasattr(carrera, "nombre"):
            carrera.nombre = nombre
            carrera.save(update_fields=["nombre"])
        else:
            carrera.save()
    else:
        carrera = Profesorado.objects.create(nombre=nombre) # Profesorado model has 'nombre' field

    if plan_id:
        plan = get_object_or_404(PlanEstudios, pk=plan_id)
        if plan.profesorado_id != carrera.id:
            return JsonResponse({"ok": False, "error": "El plan no pertenece a esa carrera."}, status=400)
        PlanEstudios.objects.filter(profesorado=carrera).update(vigente=False)
        plan.vigente = True
        plan.save(update_fields=["vigente"])

    return JsonResponse({"ok": True, "id": carrera.id})


@login_required
@require_http_methods(["DELETE"])
@transaction.atomic
@csrf_exempt # Consider more robust CSRF handling in production
def carrera_delete_api(request, pk):
    c = get_object_or_404(Profesorado, pk=pk)
    c.delete()
    return JsonResponse({"ok": True})


@login_required
@require_GET
def plan_list_api(request):
    """Devuelve todos los planes o filtra por carrera (?carrera_id=)."""
    carrera_id = request.GET.get("carrera_id")
    qs = PlanEstudios.objects.all()
    if carrera_id:
        qs = qs.filter(profesorado_id=carrera_id)
    planes = list(PlanEstudios.objects.values('id', 'resolucion').order_by('resolucion'))
    return JsonResponse(planes, safe=False)


@login_required
@require_POST
@csrf_exempt
def plan_save_api(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        resol = (data.get('resolucion') or '').strip()
        if not resol:
            return JsonResponse({'ok': False, 'error': 'Resolución obligatoria'}, status=400)
        plan, _ = PlanEstudios.objects.get_or_create(resolucion=resol)
        return JsonResponse({'ok': True, 'id': plan.id})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)