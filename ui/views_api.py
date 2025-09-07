# ui/views_api.py

import json
import logging

from django.apps import apps
from django.db import transaction
from django.db.models import CharField, F, Value
from django.db.models.functions import Coalesce, Concat
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from academia_horarios.models import Bloque, Horario, MateriaEnPlan, TurnoModel

PlanEstudios = apps.get_model("academia_core", "PlanEstudios")
EspacioCurricular = apps.get_model("academia_core", "EspacioCurricular")
Docente = apps.get_model("academia_core", "Docente")
Carrera = apps.get_model("academia_core", "Carrera")

logger = logging.getLogger(__name__)


@require_GET
def api_carreras(request):
    qs = Carrera.objects.order_by("nombre").values("id", "nombre")
    results = list(qs)
    logger.info("api_carreras -> %s items", len(results))
    return JsonResponse({"results": results}, status=200)


@require_GET
def api_planes(request):
    # Aceptamos carrera o carrera_id
    carrera_id = request.GET.get("carrera") or request.GET.get("carrera_id")
    qs = []
    if carrera_id:
        qs = (
            PlanEstudios.objects.filter(carrera_id=carrera_id, vigente=True)
            .order_by("nombre")
            .values("id", "nombre")
        )
    logger.info("api_planes params=%s -> %s items", request.GET.dict(), len(qs))
    return JsonResponse({"results": list(qs)}, status=200)


@require_GET
def api_materias(request):
    params = request.GET.dict()
    logger.info("api_materias GET params=%s", params)

    plan_id = params.get("plan") or params.get("plan_id")
    periodo_id = params.get("periodo_id")

    if not plan_id:
        return JsonResponse({"error": "Falta parámetro plan_id"}, status=400)

    try:
        qs = EspacioCurricular.objects.filter(plan_id=plan_id)

        if periodo_id:
            Periodo = apps.get_model("academia_horarios", "Periodo")
            periodo = Periodo.objects.filter(id=periodo_id).first()
            if periodo:
                if periodo.cuatrimestre == 1:
                    qs = qs.filter(cuatrimestre__in=["1", "A"])
                elif periodo.cuatrimestre == 2:
                    qs = qs.filter(cuatrimestre__in=["2", "A"])

        qs = qs.order_by("anio", "cuatrimestre", "materia__nombre")
        data = [{"id": m.id, "nombre": m.nombre, "horas": m.horas} for m in qs]
        logger.info("api_materias OK plan=%s count=%s", plan_id, len(data))
        return JsonResponse({"results": data})
    except Exception:
        logger.exception("api_materias error")
        return JsonResponse({"results": [], "error": "Ocurrió un error interno."}, status=500)


def _get(request, *names):
    for n in names:
        v = request.GET.get(n)
        if v not in (None, ""):
            return v
    return None


@require_GET
def api_docentes(request):
    carrera_id = _get(request, "carrera", "carrera_id")
    materia_id = _get(request, "materia")

    qs = Docente.objects.all()

    if carrera_id and materia_id:
        qs = qs.filter(
            asignaciones__espacio_id=materia_id, asignaciones__espacio__plan__carrera_id=carrera_id
        )

    qs = (
        qs.distinct()
        .annotate(
            ap=Coalesce(F("apellido"), Value(""), output_field=CharField()),
            no=Coalesce(F("nombre"), Value(""), output_field=CharField()),
        )
        .annotate(display=Concat(F("ap"), Value(", "), F("no"), output_field=CharField()))
        .order_by("apellido", "nombre")
        .values("id", "display")
    )

    data = [{"id": d["id"], "nombre": d["display"]} for d in qs]
    return JsonResponse({"results": data}, status=200)


@require_GET
def api_turnos(request):
    """
    GET /ui/api/turnos
    Obtiene los turnos disponibles desde la base de datos.
    """
    try:
        turnos_qs = TurnoModel.objects.order_by("id").values("slug", "nombre")
        turnos = [{"value": t["slug"], "label": t["nombre"]} for t in turnos_qs]
        return JsonResponse({"turnos": turnos}, status=200)
    except Exception:
        logger.exception("api_turnos error")
        return JsonResponse({"error": "Error al obtener los turnos."}, status=500)


@require_GET
def api_horarios_ocupados(request):
    turno_slug = (request.GET.get("turno") or "").lower()
    if turno_slug == "sabado":
        turno_slug = "manana"

    docente_id = request.GET.get("docente") or None
    aula_id = request.GET.get("aula") or None

    ocupados = []
    if turno_slug:
        qs = Horario.objects.filter(turno=turno_slug)  # quitar activo=True

        if docente_id:
            ocupados.extend(list(qs.filter(docente_id=docente_id).values("dia", "inicio", "fin")))
        if aula_id:
            ocupados.extend(list(qs.filter(aula_id=aula_id).values("dia", "inicio", "fin")))

    return JsonResponse({"ocupados": ocupados})


def _validate_draft_overlaps(draft):
    """
    Valida que en un borrador de horarios no haya bloques que se solapen en un mismo día.
    Retorna un mensaje de error si encuentra solapamiento, o None si es válido.
    """
    from collections import defaultdict

    blocks_by_day = defaultdict(list)
    for block in draft:
        blocks_by_day[block["dia"]].append(block)

    for day, blocks in blocks_by_day.items():
        if len(blocks) < 2:
            continue

        sorted_blocks = sorted(blocks, key=lambda x: x["inicio"])

        for i in range(len(sorted_blocks) - 1):
            current_block = sorted_blocks[i]
            next_block = sorted_blocks[i + 1]

            if current_block["fin"] > next_block["inicio"]:
                dia_map = {
                    "lu": "Lunes",
                    "ma": "Martes",
                    "mi": "Miércoles",
                    "ju": "Jueves",
                    "vi": "Viernes",
                    "sa": "Sábado",
                }
                return f"Conflicto de horarios el día {dia_map.get(day, day)}: el bloque de {current_block['inicio']}-{current_block['fin']} se solapa con {next_block['inicio']}-{next_block['fin']}."

    return None


@require_POST
def api_horario_save(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    materia_id = payload.get("materia_id")
    plan_id = payload.get("plan_id")
    profesorado_id = payload.get("profesorado_id")
    periodo_id = payload.get("periodo_id")
    turno = payload.get("turno")
    comision_id = payload.get("comision_id")
    items = payload.get("items", [])

    if not all([materia_id, plan_id, profesorado_id, turno, comision_id, periodo_id]):
        return JsonResponse({"ok": False, "error": "Faltan parámetros obligatorios"}, status=400)

    # Obtener la seccion de la comision (ej. 'A', 'B')
    Comision = apps.get_model("academia_horarios", "Comision")
    comision_seccion = ""
    if comision_id == "default":
        # Si es la comisión por defecto, puede que no exista. La creamos si es necesario.
        mep = MateriaEnPlan.objects.filter(plan_id=plan_id, materia_id=materia_id).first()
        comision_obj, created = Comision.objects.get_or_create(
            materia_en_plan=mep,
            periodo_id=periodo_id,
            seccion="A",
            defaults={"turno": turno, "nombre": "Comisión A"},
        )
        comision_seccion = "A"
    else:
        comision_obj = Comision.objects.filter(id=comision_id).first()
        if not comision_obj:
            return JsonResponse(
                {"ok": False, "error": "La comisión seleccionada no existe."}, status=404
            )
        comision_seccion = comision_obj.seccion

    anio = (
        MateriaEnPlan.objects.filter(plan_id=plan_id, materia_id=materia_id)
        .values_list("anio", flat=True)
        .first()
    )

    err = _validate_draft_overlaps(items)
    if err:
        return JsonResponse({"ok": False, "error": err}, status=400)

    with transaction.atomic():
        # El borrado ahora es específico para la comisión
        Horario.objects.filter(
            materia_id=materia_id,
            plan_id=plan_id,
            profesorado_id=profesorado_id,
            turno=turno,
            comision=comision_seccion,
        ).delete()

        nuevos = [
            Horario(
                materia_id=materia_id,
                plan_id=plan_id,
                profesorado_id=profesorado_id,
                turno=turno,
                comision=comision_seccion,
                dia=item["dia"],
                inicio=item["inicio"],
                fin=item["fin"],
                anio=anio,
                docente_id=item.get("docente_id"),  # <-- Guardar el docente
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
        return JsonResponse({"error": "Falta carrera_id"}, status=400)

    qs = Horario.objects.filter(carrera_id=carrera_id)
    if plan_id:
        qs = qs.filter(plan_id=plan_id)

    qs = (
        qs.order_by("anio", "dia", "inicio")
        .select_related("materia", "docente")
        .values(
            "dia",
            "inicio",
            "fin",
            "turno",
            "anio",
            "comision",
            "aula",
            "materia__nombre",
            "docente__apellido",
            "docente__nombre",
        )
    )

    items_por_anio = {1: [], 2: [], 3: [], 4: [], 0: []}
    for r in qs:
        nombre_doc = ""
        ap = r.get("docente__apellido") or ""
        no = r.get("docente__nombre") or ""
        if ap or no:
            nombre_doc = f"{ap}, {no}".strip(", ")
        else:
            nombre_doc = "Sin Docente"

        bucket = r.get("anio") or 0
        items_por_anio.setdefault(bucket, []).append(
            {
                "dia": r["dia"],
                "inicio": r["inicio"].strftime("%H:%M"),
                "fin": r["fin"].strftime("%H:%M"),
                "turno": r["turno"],
                "anio": r["anio"],
                "comision": r["comision"],
                "aula": r["aula"],
                "materia": r["materia__nombre"],
                "docente": nombre_doc,
            }
        )
    return JsonResponse(items_por_anio)


@require_GET
def api_horarios_docente(request):
    docente_id = request.GET.get("docente_id")
    if not docente_id:
        return JsonResponse({"error": "Falta el parámetro docente_id"}, status=400)

    qs = (
        Horario.objects.filter(docente_id=docente_id)
        .order_by("turno", "dia", "inicio")
        .values("dia", "inicio", "fin", "turno", "anio", "comision", "aula", "materia__nombre")
    )

    # Agrupar resultados por turno
    items_por_turno = {"manana": [], "tarde": [], "vespertino": []}
    for r in qs:
        turno = r.get("turno")
        if turno in items_por_turno:
            items_por_turno[turno].append(
                {
                    "dia": r["dia"],
                    "inicio": r["inicio"].strftime("%H:%M"),
                    "fin": r["fin"].strftime("%H:%M"),
                    "turno": r["turno"],
                    "anio": r["anio"],
                    "comision": r["comision"],
                    "aula": r["aula"],
                    "materia": r["materia__nombre"],
                }
            )

    return JsonResponse(items_por_turno)


@require_GET
def api_horarios_materia_plan(request):
    materia_id = request.GET.get("materia_id")
    plan_id = request.GET.get("plan_id")
    carrera_id = request.GET.get("profesorado_id") or request.GET.get("carrera_id")
    anio = request.GET.get("anio")
    comision = request.GET.get("comision", "")

    if not (materia_id and plan_id and carrera_id):
        return JsonResponse(
            {"error": "Faltan parámetros materia_id, plan_id o carrera_id"}, status=400
        )

    qs = Horario.objects.filter(
        materia_id=materia_id, plan_id=plan_id, carrera_id=carrera_id
    ).values("dia", "inicio", "fin", "turno", "anio", "comision", "aula")

    if anio:
        qs = qs.filter(anio=anio)
    if comision:
        qs = qs.filter(comision=comision)

    items = []
    for r in qs:
        items.append(
            {
                "dia": r["dia"],
                "inicio": r["inicio"].strftime("%H:%M"),
                "fin": r["fin"].strftime("%H:%M"),
                "turno": r["turno"],
                "anio": r["anio"],
                "comision": r["comision"],
                "aula": r["aula"],
            }
        )
    return JsonResponse({"items": items})


@require_GET
def api_grilla_config(request):
    turno = (request.GET.get("turno") or "manana").lower()
    # normaliza tildes si hace falta

    try:
        if turno == "sabado":
            qs = Bloque.objects.filter(turno__isnull=True).order_by("orden")
        else:
            qs = Bloque.objects.filter(turno__slug=turno).order_by("orden")

        bloques = list(qs.values("dia_semana", "inicio", "fin", "es_recreo"))

        for b in bloques:
            b["inicio_str"] = b["inicio"].strftime("%H:%M")
            b["fin_str"] = b["fin"].strftime("%H:%M")

        return JsonResponse(
            {
                "rows": [
                    {"ini": b["inicio_str"], "fin": b["fin_str"], "recreo": b["es_recreo"]}
                    for b in bloques
                ]
            }
        )

    except Exception:
        logger.exception(f"api_grilla_config error para turno={turno}")
        return JsonResponse(
            {"error": "Error al obtener la configuración de la grilla."},
            status=500,
        )


@require_GET
def api_get_horarios_materia(request):
    """
    Devuelve los bloques de horario existentes para una materia/turno.
    """
    profesorado_id = request.GET.get("profesorado_id")
    plan_id = request.GET.get("plan_id")
    materia_id = request.GET.get("materia_id")
    turno = request.GET.get("turno")

    if not all([profesorado_id, plan_id, materia_id, turno]):
        return JsonResponse({"error": "Faltan parámetros"}, status=400)

    qs = Horario.objects.filter(
        profesorado_id=profesorado_id, plan_id=plan_id, materia_id=materia_id, turno=turno
    ).values("dia", "inicio", "fin")

    return JsonResponse({"horarios": list(qs)})


@require_GET
def api_get_comisiones_materia(request):
    """
    Devuelve las comisiones existentes para una materia en un plan y periodo.
    """
    plan_id = request.GET.get("plan_id")
    materia_id = request.GET.get("materia_id")  # Ojo: este es EspacioCurricular ID
    periodo_id = request.GET.get("periodo_id")

    if not all([plan_id, materia_id, periodo_id]):
        return JsonResponse({"error": "Faltan parámetros"}, status=400)

    # Comision se relaciona con MateriaEnPlan. Hay que encontrar el MateriaEnPlan
    # que corresponde a este EspacioCurricular en este Plan.
    mep = MateriaEnPlan.objects.filter(plan_id=plan_id, materia_id=materia_id).first()
    if not mep:
        return JsonResponse({"comisiones": []})  # No hay materia en plan, no puede haber comisiones

    Comision = apps.get_model("academia_horarios", "Comision")
    qs = (
        Comision.objects.filter(materia_en_plan=mep, periodo_id=periodo_id)
        .order_by("seccion")
        .values("id", "seccion", "nombre")
    )

    return JsonResponse({"comisiones": list(qs)})


@require_POST
def api_add_comision(request):
    """
    Crea la siguiente comisión para una materia en un plan y periodo.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
        plan_id = payload.get("plan_id")
        materia_id = payload.get("materia_id")
        periodo_id = payload.get("periodo_id")
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    if not all([plan_id, materia_id, periodo_id]):
        return JsonResponse({"ok": False, "error": "Faltan parámetros"}, status=400)

    mep = MateriaEnPlan.objects.filter(plan_id=plan_id, materia_id=materia_id).first()
    if not mep:
        return JsonResponse({"ok": False, "error": "Materia en Plan no encontrada"}, status=404)

    Comision = apps.get_model("academia_horarios", "Comision")
    existentes = Comision.objects.filter(materia_en_plan=mep, periodo_id=periodo_id).order_by(
        "seccion"
    )

    ultima_seccion = "@"  # Caracter anterior a la 'A'
    if existentes.exists():
        ultima_seccion = existentes.last().seccion

    nueva_seccion = chr(ord(ultima_seccion) + 1)

    # Lógica para tomar el turno de la comisión anterior, si existe.
    turno_base = existentes.first().turno if existentes.exists() else "manana"

    try:
        nueva_comision = Comision.objects.create(
            materia_en_plan=mep,
            periodo_id=periodo_id,
            seccion=nueva_seccion,
            nombre=f"Comisión {nueva_seccion}",
            turno=turno_base,
        )
        return JsonResponse(
            {"ok": True, "id": nueva_comision.id, "seccion": nueva_comision.seccion}
        )
    except Exception:
        logger.exception("Error al crear nueva comisión")
        return JsonResponse(
            {"ok": False, "error": "Ocurrió un error interno del servidor"}, status=500
        )
