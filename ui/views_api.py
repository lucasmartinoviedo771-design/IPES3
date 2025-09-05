# ui/views_api.py

from django.db.models import Value, F, CharField, Q
from django.db.models.functions import Concat, Coalesce
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.db import transaction
import logging
import json
from django.utils import timezone

from django.apps import apps

PlanEstudios = apps.get_model('academia_core', 'PlanEstudios')
EspacioCurricular = apps.get_model('academia_core', 'EspacioCurricular')
Docente = apps.get_model('academia_core', 'Docente')
Carrera = apps.get_model('academia_core', 'Carrera')
from academia_horarios.models import Horario, TurnoModel, Bloque, MateriaEnPlan


logger = logging.getLogger(__name__)

@require_GET
def api_carreras(request):
    qs = (
        Carrera.objects.order_by("nombre").values("id", "nombre")
    )
    results = list(qs)
    logger.info("api_carreras -> %s items", len(results))
    return JsonResponse({"results": results}, status=200)

@require_GET
def api_planes(request):
    # Aceptamos carrera o carrera_id
    carrera_id = request.GET.get('carrera') or request.GET.get('carrera_id')
    qs = []
    if carrera_id:
        qs = (PlanEstudios.objects
              .filter(carrera_id=carrera_id, vigente=True)
              .order_by('nombre')
              .values('id', 'nombre'))
    logger.info("api_planes params=%s -> %s items", request.GET.dict(), len(qs))
    return JsonResponse({'results': list(qs)}, status=200)

@require_GET
def api_materias(request):
    params = request.GET.dict()
    logger.info("api_materias GET params=%s", params)

    plan_id = params.get('plan') or params.get('plan_id')
    carrera_id = params.get('carrera') or params.get('carrera_id')

    if not plan_id:
        return JsonResponse({'error': 'Falta parámetro plan/plan_id', 'recibido': params}, status=400)

    try:
        qs = EspacioCurricular.objects.filter(plan_id=plan_id)
        if carrera_id:
            qs = qs.filter(plan__carrera_id=carrera_id)
        qs = qs.order_by('anio', 'cuatrimestre', 'nombre')
        data = [{'id': m.id, 'nombre': m.nombre, 'horas': m.horas} for m in qs]
        logger.info("api_materias OK plan=%s carrera=%s count=%s", plan_id, carrera_id, len(data))
        return JsonResponse({'results': data})
    except Exception as e:
        logger.error("api_materias error: %s", e, exc_info=True)
        return JsonResponse({'results': [], 'error': str(e)}, status=500)

def _get(request, *names):
    for n in names:
        v = request.GET.get(n)
        if v not in (None, ''):
            return v
    return None

@require_GET
def api_docentes(request):
    carrera_id = _get(request, 'carrera', 'carrera_id')
    materia_id = _get(request, 'materia')

    qs = Docente.objects.all()

    if carrera_id and materia_id:
        qs = qs.filter(
            asignaciones__espacio_id=materia_id,
            asignaciones__espacio__plan__carrera_id=carrera_id
        )

    qs = (qs.distinct()
            .annotate(
                ap=Coalesce(F('apellido'), Value(''), output_field=CharField()),
                no=Coalesce(F('nombre'),   Value(''), output_field=CharField()),
            )
            .annotate(display=Concat(F('ap'), Value(', '), F('no'), output_field=CharField()))
            .order_by('apellido', 'nombre')
            .values('id', 'display')
         )

    data = [{'id': d['id'], 'nombre': d['display']} for d in qs]
    return JsonResponse({'results': data}, status=200)

@require_GET
def api_turnos(request):
    """
    GET /ui/api/turnos
    Obtiene los turnos disponibles desde la base de datos.
    """
    try:
        turnos_qs = TurnoModel.objects.order_by('id').values('slug', 'nombre')
        turnos = [
            {"value": t['slug'], "label": t['nombre']}
            for t in turnos_qs
        ]
        return JsonResponse({"turnos": turnos}, status=200)
    except Exception as e:
        logger.error("api_turnos error: %s", e, exc_info=True)
        return JsonResponse({'error': 'Error al obtener los turnos.'}, status=500)

@require_GET
def api_horarios_ocupados(request):
    turno_slug = (request.GET.get('turno') or '').lower()
    if turno_slug == 'sabado':
        turno_slug = 'manana'

    docente_id = request.GET.get('docente') or None
    aula_id    = request.GET.get('aula') or None

    ocupados = []
    if turno_slug:
        qs = Horario.objects.filter(turno=turno_slug)  # quitar activo=True

        if docente_id:
            ocupados.extend(list(qs.filter(docente_id=docente_id).values('dia', 'inicio', 'fin')))
        if aula_id:
            ocupados.extend(list(qs.filter(aula_id=aula_id).values('dia', 'inicio', 'fin')))

    return JsonResponse({"ocupados": ocupados})


def _validate_draft_overlaps(draft):
    """
    Valida que en un borrador de horarios no haya bloques que se solapen en un mismo día.
    Retorna un mensaje de error si encuentra solapamiento, o None si es válido.
    """
    from collections import defaultdict
    
    blocks_by_day = defaultdict(list)
    for block in draft:
        blocks_by_day[block['dia']].append(block)
    
    for day, blocks in blocks_by_day.items():
        if len(blocks) < 2:
            continue
        
        sorted_blocks = sorted(blocks, key=lambda x: x['inicio'])
        
        for i in range(len(sorted_blocks) - 1):
            current_block = sorted_blocks[i]
            next_block = sorted_blocks[i+1]
            
            if current_block['fin'] > next_block['inicio']:
                dia_map = {'lu': 'Lunes', 'ma': 'Martes', 'mi': 'Miércoles', 'ju': 'Jueves', 'vi': 'Viernes', 'sa': 'Sábado'}
                return f"Conflicto de horarios el día {dia_map.get(day, day)}: el bloque de {current_block['inicio']}-{current_block['fin']} se solapa con {next_block['inicio']}-{next_block['fin']}."
                
    return None


@require_POST
def api_horario_save(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    materia_id = payload.get("materia_id")
    plan_id = payload.get("plan_id")
    carrera_id = payload.get("profesorado_id") or payload.get("carrera_id")
    turno = payload.get("turno")
    items = payload.get("items", [])

    if not (materia_id and plan_id and carrera_id and turno):
        return JsonResponse({'ok': False, 'error': 'Faltan parámetros obligatorios (materia, plan, carrera, turno)'}, status=400)

    # 1) buscar el año de esa materia en ese plan
    anio = (MateriaEnPlan.objects
            .filter(plan_id=plan_id, materia_id=materia_id)
            .values_list('anio', flat=True)
            .first())

    # 🔴 NUEVO: valida solapes en el draft
    err = _validate_draft_overlaps(items)
    if err:
        return JsonResponse({'ok': False, 'error': err}, status=400)

    with transaction.atomic():
        Horario.objects.filter(
            materia_id=materia_id, plan_id=plan_id,
            carrera_id=carrera_id, turno=turno
        ).delete()

        nuevos = [
            Horario(
                materia_id=materia_id,
                plan_id=plan_id,
                carrera_id=carrera_id,
                turno=turno,
                dia=item['dia'],
                inicio=item['inicio'],
                fin=item['fin'],
                anio=anio,              # ← ★ ahora se guarda el año
            )
            for item in items
        ]
        Horario.objects.bulk_create(nuevos)

    return JsonResponse({"ok": True, "count": len(nuevos)})


@require_GET
def api_horarios_profesorado(request):
    carrera_id = request.GET.get("profesorado_id") or request.GET.get("carrera_id")
    plan_id = request.GET.get("plan_id")
    if not carrera_id:
        return JsonResponse({'error': 'Falta carrera_id'}, status=400)

    qs = (Horario.objects
          .filter(carrera_id=carrera_id))
    if plan_id:
        qs = qs.filter(plan_id=plan_id)
    
    qs = (qs.order_by('anio','dia','inicio')
            .select_related('materia','docente')
            .values('dia','inicio','fin','turno','anio','comision','aula','materia__nombre',
                    'docente__apellido','docente__nombre'))

    items_por_anio = {1:[],2:[],3:[],4:[],0:[]}
    for r in qs:
        nombre_doc = ''
        ap = r.get('docente__apellido') or ''
        no = r.get('docente__nombre') or ''
        if ap or no:
            nombre_doc = f"{ap}, {no}".strip(', ')
        else:
            nombre_doc = "Sin Docente"

        bucket = r.get('anio') or 0
        items_por_anio.setdefault(bucket, []).append({
            'dia': r['dia'],
            'inicio': r['inicio'].strftime('%H:%M'),
            'fin': r['fin'].strftime('%H:%M'),
            'turno': r['turno'],
            'anio': r['anio'],
            'comision': r['comision'],
            'aula': r['aula'],
            'materia': r['materia__nombre'],
            'docente': nombre_doc,
        })
    return JsonResponse(items_por_anio)

@require_GET
def api_horarios_docente(request):
    docente_id = request.GET.get("docente_id")
    if not docente_id:
        return JsonResponse({'error': 'Falta el parámetro docente_id'}, status=400)

    qs = (Horario.objects
          .filter(docente_id=docente_id)
          .order_by('turno', 'dia', 'inicio')
          .values('dia','inicio','fin','turno','anio','comision','aula',
                  'materia__nombre'))

    # Agrupar resultados por turno
    items_por_turno = {
        'manana': [], 'tarde': [], 'vespertino': []
    }
    for r in qs:
        turno = r.get('turno')
        if turno in items_por_turno:
            items_por_turno[turno].append({
                'dia': r['dia'],
                'inicio': r['inicio'].strftime('%H:%M'),
                'fin': r['fin'].strftime('%H:%M'),
                'turno': r['turno'],
                'anio': r['anio'],
                'comision': r['comision'],
                'aula': r['aula'],
                'materia': r['materia__nombre'],
            })
            
    return JsonResponse(items_por_turno)

@require_GET
def api_horarios_materia_plan(request):
    materia_id = request.GET.get("materia_id")
    plan_id = request.GET.get("plan_id")
    carrera_id = request.GET.get("profesorado_id") or request.GET.get("carrera_id")
    anio = request.GET.get("anio")
    comision = request.GET.get("comision", "")

    if not (materia_id and plan_id and carrera_id):
        return JsonResponse({'error': 'Faltan parámetros materia_id, plan_id o carrera_id'}, status=400)

    qs = (Horario.objects
          .filter(materia_id=materia_id, plan_id=plan_id, carrera_id=carrera_id)
          .values('dia','inicio','fin','turno','anio','comision','aula'))

    if anio:
        qs = qs.filter(anio=anio)
    if comision:
        qs = qs.filter(comision=comision)

    items = []
    for r in qs:
        items.append({
            'dia': r['dia'],
            'inicio': r['inicio'].strftime('%H:%M'),
            'fin': r['fin'].strftime('%H:%M'),
            'turno': r['turno'],
            'anio': r['anio'],
            'comision': r['comision'],
            'aula': r['aula'],
        })
    return JsonResponse({'items': items})

@require_GET
def api_grilla_config(request):
    turno = (request.GET.get('turno') or 'manana').lower()
    # normaliza tildes si hace falta

    try:
        if turno == 'sabado':
            qs = Bloque.objects.filter(turno__isnull=True).order_by('orden')
        else:
            qs = Bloque.objects.filter(turno__slug=turno).order_by('orden')
        
        bloques = list(qs.values(
            'dia_semana', 'inicio', 'fin', 'es_recreo'
        ))

        for b in bloques:
            b['inicio_str'] = b['inicio'].strftime('%H:%M')
            b['fin_str'] = b['fin'].strftime('%H:%M')

        return JsonResponse({
            "rows": [
                {"ini": b['inicio_str'], "fin": b['fin_str'], "recreo": b['es_recreo']}
                for b in bloques
            ]
        })

    except Exception as e:
        logger.error(f"api_grilla_config error para turno={turno}: {e}", exc_info=True)
        return JsonResponse({'error': 'Error al obtener la configuración de la grilla.'}, status=500)
