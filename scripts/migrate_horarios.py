# scripts/migrate_horarios.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import connections, transaction
from django.db.models import Model
from django.utils.timezone import now

from academia_core.models import Carrera, Materia, PlanEstudios
from academia_horarios.models import (
    Comision,
    HorarioClase,
    MateriaEnPlan,
    Periodo,
    TimeSlot,
)


# -------- helpers de introspección --------
def has_field(model: type[Model], name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


def get_field(model: type[Model], name: str):
    return model._meta.get_field(name)


# -------- helper SQL --------
def fetch_all_dict(cur, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]


@dataclass
class Counters:
    mep_created: int = 0
    mep_existing: int = 0
    per_created: int = 0
    per_existing: int = 0
    ts_created: int = 0
    ts_existing: int = 0
    com_created: int = 0
    com_existing: int = 0
    hc_created: int = 0
    hc_existing: int = 0
    skipped: int = 0


def main(commit: bool = True):
    """
    Migra datos de horarios desde la base legacy:
      - academia_horarios_materiaenplan
      - academia_horarios_comision
      - academia_horarios_timeslot
      - academia_horarios_horarioclase
      - academia_horarios_periodo (si existe)
    """
    print("== Migración de horarios (legacy -> nueva) ==")
    cnt = Counters()

    # ---------------- LEER LEGACY ----------------
    with connections["legacy"].cursor() as cur:
        legacy_plans = fetch_all_dict(
            cur,
            """
            SELECT p.id AS legacy_id, p.resolucion, pr.nombre AS carrera_nombre
            FROM academia_core_planestudios p
            JOIN academia_core_profesorado pr ON pr.id = p.profesorado_id
            """,
        )

        legacy_mats = fetch_all_dict(
            cur, "SELECT id AS legacy_id, nombre FROM academia_core_materia"
        )

        # MateriaEnPlan (tolerar columnas opcionales)
        cur.execute("SELECT * FROM academia_horarios_materiaenplan LIMIT 0")
        mep_cols = {d[0] for d in cur.description}

        base = ["id AS legacy_id", "plan_id", "materia_id", "anio"]
        for opt in ["cuatrimestre", "turno", "vigente"]:
            if opt in mep_cols:
                base.append(opt)
        leg_mep = fetch_all_dict(
            cur, f"SELECT {', '.join(base)} FROM academia_horarios_materiaenplan"
        )

        leg_com = fetch_all_dict(
            cur,
            """
            SELECT id AS legacy_id, turno, nombre, cupo, seccion, materia_en_plan_id, periodo_id
            FROM academia_horarios_comision
            """,
        )

        leg_ts = fetch_all_dict(
            cur,
            """
            SELECT id AS legacy_id, dia_semana, inicio, fin, turno
            FROM academia_horarios_timeslot
            """,
        )

        leg_hc = fetch_all_dict(
            cur,
            """
            SELECT id AS legacy_id, aula, observaciones, comision_id, timeslot_id
            FROM academia_horarios_horarioclase
            """,
        )

        try:
            leg_per = fetch_all_dict(
                cur,
                "SELECT id AS legacy_id, nombre, fecha_inicio, fecha_fin FROM academia_horarios_periodo",
            )
        except Exception:
            leg_per = []

    # ---------------- MAPEO PLANES ----------------
    plan_map: dict[int, int] = {}
    carreras_by_name = {c.nombre.strip(): c for c in Carrera.objects.all()}
    miss_plans: list[dict[str, Any]] = []

    for p in legacy_plans:
        carrera = carreras_by_name.get((p.get("carrera_nombre") or "").strip())
        if not carrera:
            miss_plans.append(p)
            continue
        try:
            new_plan = PlanEstudios.objects.get(
                carrera=carrera, resolucion=(p.get("resolucion") or "").strip()
            )
            plan_map[p["legacy_id"]] = new_plan.id
        except PlanEstudios.DoesNotExist:
            miss_plans.append(p)

    print(f"Planes mapeados (legacy -> nuevo): {len(plan_map)}/{len(legacy_plans)}")
    if miss_plans:
        print("ATENCIÓN: sin match por (carrera,resolución):", miss_plans)

    # ---------------- MAPEO MATERIAS ----------------
    # Tu modelo actual de Materia no tiene 'anio'; la clave es por nombre.
    mat_by_name = {m.nombre.strip().lower(): m for m in Materia.objects.all()}
    mat_map: dict[int, int] = {}
    for m in legacy_mats:
        nm = (m.get("nombre") or "").strip().lower()
        if nm in mat_by_name:
            mat_map[m["legacy_id"]] = mat_by_name[nm].id

    # ---------------- CREAR MateriaEnPlan ----------------
    mep_map: dict[int, int] = {}  # legacy_mep_id -> new_mep_id
    mep_has_turno = has_field(MateriaEnPlan, "turno")
    mep_has_anio = has_field(MateriaEnPlan, "anio")
    mep_has_cuatri = has_field(MateriaEnPlan, "cuatrimestre")

    @transaction.atomic
    def create_mep():
        nonlocal cnt
        for r in leg_mep:
            lp = plan_map.get(r["plan_id"])
            lm = mat_map.get(r["materia_id"])
            if not (lp and lm):
                cnt.skipped += 1
                continue

            # Lookup mínimo (evita duplicados reales y permite varios años si el modelo lo soporta)
            lookup = {"plan_id": lp, "materia_id": lm}
            defaults: dict[str, Any] = {}

            if mep_has_anio and r.get("anio") is not None:
                # Si el modelo tiene 'anio', lo uso en el lookup para distinguir cohortes
                lookup["anio"] = r["anio"]
            if mep_has_cuatri and r.get("cuatrimestre") is not None:
                # Cuatrimestre como default (no en lookup para no sobre-especificar)
                defaults["cuatrimestre"] = r["cuatrimestre"]

            if mep_has_turno and r.get("turno"):
                f = get_field(MateriaEnPlan, "turno")
                if getattr(f, "remote_field", None) and f.remote_field:
                    TurnoModel = f.remote_field.model
                    turno_obj, _ = TurnoModel.objects.get_or_create(codigo=str(r["turno"]).strip())
                    defaults["turno"] = turno_obj
                else:
                    defaults["turno"] = str(r["turno"]).strip()

            obj, created = MateriaEnPlan.objects.get_or_create(**lookup, defaults=defaults)
            mep_map[r["legacy_id"]] = obj.id
            if created:
                cnt.mep_created += 1
            else:
                cnt.mep_existing += 1

    create_mep()
    print(f"MateriaEnPlan: creados={cnt.mep_created}, existentes={cnt.mep_existing}")

    # ---------------- PERIODOS ----------------
    per_map: dict[int, int] = {}
    per_has_nombre = has_field(Periodo, "nombre")
    per_has_fini = has_field(Periodo, "fecha_inicio")
    per_has_ffin = has_field(Periodo, "fecha_fin")

    @transaction.atomic
    def create_periodos():
        nonlocal cnt
        if not leg_per:
            # Si no hay periodos en legacy, garantizo al menos 1 para FKs no nulos
            if per_has_nombre:
                p, created = Periodo.objects.get_or_create(nombre=f"LEGACY-{now().date()}")
            else:
                # modelo sin 'nombre' -> uso id=1 por defecto
                p, created = Periodo.objects.get_or_create(id=1)
            if created:
                cnt.per_created += 1
            else:
                cnt.per_existing += 1
            # mapear cualquier referencia entrante a este
            for r in leg_com:
                if r.get("periodo_id"):
                    per_map[r["periodo_id"]] = p.id
            return

        for r in leg_per:
            defaults: dict[str, Any] = {}
            if per_has_nombre and r.get("nombre"):
                defaults["nombre"] = r["nombre"]
            if per_has_fini and r.get("fecha_inicio"):
                defaults["fecha_inicio"] = r["fecha_inicio"]
            if per_has_ffin and r.get("fecha_fin"):
                defaults["fecha_fin"] = r["fecha_fin"]

            # Si no hay campos “textuales/fechas”, creo por id para mantener relación
            if defaults:
                obj, created = Periodo.objects.get_or_create(**defaults)
            else:
                obj, created = Periodo.objects.get_or_create(id=r["legacy_id"])
            per_map[r["legacy_id"]] = obj.id
            if created:
                cnt.per_created += 1
            else:
                cnt.per_existing += 1

    create_periodos()
    print(f"Periodos: creados={cnt.per_created}, existentes={cnt.per_existing}")

    # ---------------- TIMESLOTS ----------------
    ts_map: dict[int, int] = {}
    ts_has_turno = has_field(TimeSlot, "turno")

    @transaction.atomic
    def create_timeslots():
        nonlocal cnt
        for r in leg_ts:
            # Armamos el lookup mínimo
            lookup = dict(
                dia_semana=r.get("dia_semana"),
                inicio=r.get("inicio"),
                fin=r.get("fin"),
            )

            # Si el modelo tiene 'turno', lo incluimos en el lookup
            if ts_has_turno and r.get("turno"):
                f = get_field(TimeSlot, "turno")
                if getattr(f, "remote_field", None) and f.remote_field:
                    # Es una FK (p.ej. TurnoModel)
                    TurnoModel = f.remote_field.model
                    turno_obj, _ = TurnoModel.objects.get_or_create(codigo=str(r["turno"]).strip())
                    lookup["turno"] = turno_obj
                else:
                    # Es CharField
                    lookup["turno"] = str(r["turno"]).strip()

            # 1) Si ya existe uno (o más), usamos el primero para mapear y no duplicar
            qs = TimeSlot.objects.filter(**lookup).order_by("id")
            existing = qs.first()
            if existing:
                ts_map[r["legacy_id"]] = existing.id
                cnt.ts_existing += 1
                continue

            # 2) Si no existe, lo creamos
            obj = TimeSlot.objects.create(**lookup)
            ts_map[r["legacy_id"]] = obj.id
            cnt.ts_created += 1

    create_timeslots()
    print(f"TimeSlots: creados={cnt.ts_created}, existentes={cnt.ts_existing}")

    # ---------------- COMISIONES ----------------
    com_map: dict[int, int] = {}
    com_has_turno = has_field(Comision, "turno")
    com_has_seccion = has_field(Comision, "seccion")
    com_has_cupo = has_field(Comision, "cupo")
    com_has_nombre = has_field(Comision, "nombre")
    com_has_periodo = has_field(Comision, "periodo")

    @transaction.atomic
    def create_comisiones():
        nonlocal cnt
        for r in leg_com:
            new_mep_id = mep_map.get(r["materia_en_plan_id"])
            if not new_mep_id:
                cnt.skipped += 1
                continue

            defaults: dict[str, Any] = {}

            nombre_val = None
            if com_has_nombre and r.get("nombre"):
                nombre_val = r["nombre"]

            if com_has_cupo and r.get("cupo") is not None:
                defaults["cupo"] = r["cupo"]
            if com_has_seccion and r.get("seccion"):
                defaults["seccion"] = r["seccion"]

            if com_has_turno and r.get("turno"):
                f = get_field(Comision, "turno")
                if getattr(f, "remote_field", None) and f.remote_field:
                    TurnoModel = f.remote_field.model
                    turno_obj, _ = TurnoModel.objects.get_or_create(codigo=str(r["turno"]).strip())
                    defaults["turno"] = turno_obj
                else:
                    defaults["turno"] = str(r["turno"]).strip()

            if com_has_periodo:
                lp = r.get("periodo_id")
                if lp and lp in per_map:
                    defaults["periodo_id"] = per_map[lp]
                else:
                    # Si el campo no permite null, intento asignar alguno
                    f = get_field(Comision, "periodo")
                    if not getattr(f, "null", True):
                        any_per = Periodo.objects.order_by("id").first()
                        if any_per:
                            defaults["periodo_id"] = any_per.id

            # Armamos lookup mínimo e idempotente
            lookup = {"materia_en_plan_id": new_mep_id}
            if com_has_nombre:
                lookup["nombre"] = nombre_val or "C"

            # Evitar que 'nombre' quede duplicado en defaults:
            if "nombre" in defaults:
                defaults.pop("nombre")

            obj, created = Comision.objects.get_or_create(**lookup, defaults=defaults)
            com_map[r["legacy_id"]] = obj.id
            if created:
                cnt.com_created += 1
            else:
                cnt.com_existing += 1

    create_comisiones()
    print(f"Comisiones: creadas={cnt.com_created}, existentes={cnt.com_existing}")

    # ---------------- HORARIO CLASE ----------------
    hc_has_aula = has_field(HorarioClase, "aula")
    hc_has_observaciones = has_field(HorarioClase, "observaciones")

    @transaction.atomic
    def create_horario_clase():
        nonlocal cnt
        for r in leg_hc:
            new_com_id = com_map.get(r["comision_id"])
            new_ts_id = ts_map.get(r["timeslot_id"])
            if not (new_com_id and new_ts_id):
                cnt.skipped += 1
                continue

            defaults: dict[str, Any] = {}
            if hc_has_aula and r.get("aula"):
                defaults["aula"] = r["aula"]
            if hc_has_observaciones and r.get("observaciones"):
                defaults["observaciones"] = r["observaciones"]

            # Idempotente: una clase por (comision, timeslot)
            obj, created = HorarioClase.objects.get_or_create(
                comision_id=new_com_id, timeslot_id=new_ts_id, defaults=defaults
            )
            if created:
                cnt.hc_created += 1
            else:
                cnt.hc_existing += 1

    create_horario_clase()
    print(
        f"HorarioClase: creados={cnt.hc_created}, existentes={cnt.hc_existing}, "
        f"saltados={cnt.skipped}"
    )

    print("== FIN migración horarios ==")


if __name__ == "__main__":
    main(commit=True)
