# ui/views_api.py

from django.db.models import Value, F, CharField, Q
from django.db.models.functions import Concat, Coalesce
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.db import transaction
import logging
import json
from django.utils import timezone

from academia_core.models import PlanEstudios, EspacioCurricular, Docente, Profesorado
from academia_horarios.models import Horario, TurnoModel, Bloque


logger = logging.getLogger(__name__)

@require_GET
def api_carreras(request):
    qs = (
        Profesorado.objects.order_by("nombre").values("id", "nombre")
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
              .filter(profesorado_id=carrera_id, vigente=True)
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
            qs = qs.filter(plan__profesorado_id=carrera_id)
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
            asignaciones__espacio__plan__profesorado_id=carrera_id
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
        try:
            qs = Horario.objects.filter(turno=turno_slug, activo=True)
            
            if docente_id:
                ocupados.extend(list(qs.filter(docente_id=docente_id).values('dia', 'hora_inicio', 'hora_fin')))

            if aula_id:
                ocupados.extend(list(qs.filter(aula_id=aula_id).values('dia', 'hora_inicio', 'hora_fin')))
        except Exception as e:
            logger.error("api_horarios_ocupados error: %s", e, exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

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
    profesorado_id = payload.get("profesorado_id")
    turno = payload.get("turno")
    items = payload.get("items", [])

    if not (materia_id and plan_id and profesorado_id and turno):
        return JsonResponse({'ok': False, 'error': 'Faltan parámetros obligatorios (materia, plan, profesorado, turno)'}, status=400)

    # Usamos un simple borrado y recreación para la idempotencia
    with transaction.atomic():
        # 1. Borrar todos los horarios existentes para esta cátedra/turno
        (Horario.objects
            .filter(materia_id=materia_id, plan_id=plan_id,
                    profesorado_id=profesorado_id, turno=turno)
            .delete())

        # 2. Crear los nuevos horarios desde el payload
        nuevos_horarios = []
        for item in items:
            nuevos_horarios.append(Horario(
                materia_id=materia_id,
                plan_id=plan_id,
                profesorado_id=profesorado_id,
                turno=turno,
                dia=item['dia'],
                inicio=item['inicio'],
                fin=item['fin'],
                # Aquí se podrían añadir más campos como anio, comision, aula si vinieran en el payload
            ))
        
        Horario.objects.bulk_create(nuevos_horarios)

    return JsonResponse({"ok": True, "count": len(nuevos_horarios)})


@require_GET
def api_horarios_profesorado(request):
    profesorado_id = request.GET.get("profesorado_id")
    if not profesorado_id:
        return JsonResponse({'error': 'Falta el parámetro profesorado_id'}, status=400)

    qs = (Horario.objects
          .filter(profesorado_id=profesorado_id)
          .order_by('anio', 'dia', 'inicio')
          .values('dia','inicio','fin','turno','anio','comision','aula',
                  'materia__nombre','plan_id','profesorado_id'))

    # Agrupar resultados por año
    items_por_anio = {
        1: [], 2: [], 3: [], 4: []
    }
    for r in qs:
        anio = r.get('anio')
        if anio in items_por_anio:
            items_por_anio[anio].append({
                'dia': r['dia'],
                'inicio': r['inicio'].strftime('%H:%M'),
                'fin': r['fin'].strftime('%H:%M'),
                'turno': r['turno'],
                'anio': r['anio'],
                'comision': r['comision'],
                'aula': r['aula'],
                'materia': r['materia__nombre'],
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
    profesorado_id = request.GET.get("profesorado_id")
    anio = request.GET.get("anio")
    comision = request.GET.get("comision", "")

    if not (materia_id and plan_id and profesorado_id):
        return JsonResponse({'error': 'Faltan parámetros materia_id, plan_id o profesorado_id'}, status=400)

    qs = (Horario.objects
          .filter(materia_id=materia_id, plan_id=plan_id, profesorado_id=profesorado_id)
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
    """
    Devuelve la estructura de la grilla (bloques y recreos) para un turno dado.
    GET params: turno (slug, ej: "manana" o "sabado")
    """
    turno_slug = request.GET.get('turno')
    if not turno_slug:
        return JsonResponse({'error': 'Falta el parámetro turno'}, status=400)

    try:
        if turno_slug == 'sabado':
            qs = Bloque.objects.filter(turno__isnull=True).order_by('orden')
        else:
            qs = Bloque.objects.filter(turno__slug=turno_slug).order_by('orden')
        
        bloques = list(qs.values(
            'dia_semana', 'inicio', 'fin', 'es_recreo'
        ))

        for b in bloques:
            b['inicio'] = b['inicio'].strftime('%H:%M')
            b['fin'] = b['fin'].strftime('%H:%M')

        return JsonResponse({'bloques': bloques})

    except Exception as e:
        logger.error(f"api_grilla_config error para turno={turno_slug}: {e}", exc_info=True)
        return JsonResponse({'error': 'Error al obtener la configuración de la grilla.'}, status=500)
