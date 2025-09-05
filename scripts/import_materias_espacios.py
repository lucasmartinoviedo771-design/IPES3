from django.db import connections, transaction
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from academia_core.models import Carrera, PlanEstudios, Materia, EspacioCurricular

# Usamos esta tabla legacy porque trae "nombre", "anio" y referencia de plan_id
LEGACY_JOIN_TABLE = "academia_core_espaciocurricular"
LEGACY_PLAN_TABLE = "academia_core_planestudios"  # para mapear plan_id (legacy) -> resolucion

def _to_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default

created_mats = existing_mats = created_esp = existing_esp = skipped = 0

with connections["legacy"].cursor() as cur, transaction.atomic():
    # 0) Armo el mapa plan_legacy_id -> resolucion (legacy)
    cur.execute(f"SELECT id, resolucion FROM {LEGACY_PLAN_TABLE}")
    plan_rows = cur.fetchall()
    plan_cols = [d[0] for d in cur.description]
    idx_id = plan_cols.index("id")
    idx_res = plan_cols.index("resolucion")
    legacy_planid_to_res = {r[idx_id]: (r[idx_res] or "").strip() for r in plan_rows}

    # 0b) Con esa resolucion, busco el PlanEstudios en TU BD NUEVA
    #     (si hay duplicados por resolucion, me quedo con el primero)
    plan_by_legacy_id = {}
    for legacy_id, resol in legacy_planid_to_res.items():
        if not resol:
            continue
        try:
            plan_obj = PlanEstudios.objects.filter(resolucion=resol).order_by("id").first()
            if plan_obj:
                plan_by_legacy_id[legacy_id] = plan_obj
        except Exception:
            # Si algo raro pasa, lo dejamos sin mapear
            pass

    # 1) Leemos todas las filas del join legacy
    cur.execute(f"SELECT * FROM {LEGACY_JOIN_TABLE}")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    colset = set(cols)

    required = {"anio", "cuatrimestre", "nombre", "plan_id"}
    if not required.issubset(colset):
        raise RuntimeError(
            f"Faltan columnas en {LEGACY_JOIN_TABLE}. "
            f"Necesarias: {sorted(required)}. Encontradas: {sorted(colset)}"
        )

    # Cache simple de materias por nombre normalizado
    materias_cache = {}  # nombre.lower() -> Materia

    # 2) Crear/obtener Materias (catálogo global por nombre)
    for r in rows:
        d = dict(zip(cols, r))
        nombre = (d.get("nombre") or "").strip()
        if not nombre:
            skipped += 1
            continue

        key = nombre.lower()
        if key in materias_cache:
            continue

        mat, created = Materia.objects.get_or_create(nombre=nombre)
        materias_cache[key] = mat
        if created:
            created_mats += 1
        else:
            existing_mats += 1

    # 3) Crear/obtener EspaciosCurriculares (uno por plan + materia)
    for r in rows:
        d = dict(zip(cols, r))
        nombre = (d.get("nombre") or "").strip()
        if not nombre:
            skipped += 1
            continue

        legacy_plan_id = d.get("plan_id")
        plan = plan_by_legacy_id.get(legacy_plan_id)
        if not plan:
            # No pude mapear ese plan_id legacy a un PlanEstudios nuevo (por resolucion)
            skipped += 1
            continue

        mat = materias_cache.get(nombre.lower())
        if not mat:
            skipped += 1
            continue

        anio = _to_int(d.get("anio"), 0)
        cuatri = (d.get("cuatrimestre") or "").strip()
        horas = _to_int(d.get("horas"), 0)
        formato = (d.get("formato") or "").strip()
        libre = bool(d.get("libre_habilitado"))

        obj, created = EspacioCurricular.objects.get_or_create(
            plan=plan,
            materia=mat,
            defaults=dict(
                anio=anio,
                cuatrimestre=cuatri,
                horas=horas,
                formato=formato,
                libre_habilitado=libre,
            ),
        )
        if created:
            created_esp += 1
        else:
            existing_esp += 1

print("=== Importación desde legacy ===")
print(f"Materias:   creadas={created_mats}, existentes={existing_mats}")
print(f"Espacios:   creados={created_esp}, existentes={existing_esp}, saltados={skipped}")
print("Totales ahora:",
      "Carreras", Carrera.objects.count(),
      "| Planes", PlanEstudios.objects.count(),
      "| Materias", Materia.objects.count(),
      "| Espacios", EspacioCurricular.objects.count())