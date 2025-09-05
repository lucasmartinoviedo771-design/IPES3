import contextlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.utils.termcolors import make_style

from academia_core.models import Carrera, PlanEstudios, Materia, EspacioCurricular


green = make_style(fg="green", opts=("bold",))
yellow = make_style(fg="yellow")
red = make_style(fg="red", opts=("bold",))
cyan = make_style(fg="cyan")
bold = make_style(opts=("bold",))


def _fmt(s: str) -> str:
    return s.replace("\n", " ").strip()


def _first_present(cols: Sequence[str], *candidates: str) -> Optional[str]:
    s = set(c.lower() for c in cols)
    for cand in candidates:
        if cand and cand.lower() in s:
            return cand
    return None


@contextlib.contextmanager
def legacy_cursor():
    # Usa la conexión configurada en settings.DATABASES["legacy"]
    cursor = None
    try:
        conn = connections["legacy"]
        cursor = conn.cursor()
        yield cursor
    finally:
        if cursor:
            cursor.close()


@dataclass
class LegacyTables:
    carrera: Optional[str] = None
    planes: Optional[str] = None
    materias: Optional[str] = None
    join_plan_materia: Optional[str] = None


class Command(BaseCommand):
    help = "Migra datos (Carreras/Planes/Materias/Espacios) desde la DB 'legacy' hacia la DB por defecto."

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="Aplica cambios. Sin esto, es dry-run.")
        parser.add_argument("--limit", type=int, default=0, help="Limita filas por tabla (debug). 0 = sin límite.")
        parser.add_argument("--skip-espacios", action="store_true", help="No crea EspacioCurricular (join).")

        # NUEVOS flags para forzar nombres de tabla:
        parser.add_argument("--carrera-table", type=str, help="Nombre de tabla legacy para carreras/profesorados.")
        parser.add_argument("--planes-table", type=str, help="Nombre de tabla legacy para planes de estudio.")
        parser.add_argument("--materias-table", type=str, help="Nombre de tabla legacy para materias.")
        parser.add_argument("--join-table", type=str, help="Nombre de tabla legacy join plan↔materia.")

    # ----- util SQL -------

    def _fetchall(self, cursor, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        cursor.execute(sql, params)
        cols = [c[0] for c in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def _show_tables(self, cursor) -> List[str]:
        cursor.execute("SHOW TABLES")
        return [r[0] for r in cursor.fetchall()]

    def _show_columns(self, cursor, table: str) -> List[str]:
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        return [r[0] for r in cursor.fetchall()]

    # ----- autodetección de tablas -------

    def _guess_tables(self, all_tables: List[str], forced: LegacyTables) -> LegacyTables:
        lt = LegacyTables(
            carrera=forced.carrera,
            planes=forced.planes,
            materias=forced.materias,
            join_plan_materia=forced.join_plan_materia,
        )

        def pick(candidates: List[str]) -> Optional[str]:
            for t in all_tables:
                lo = t.lower()
                if any(c in lo for c in candidates):
                    return t
            return None

        if not lt.carrera:
            # Puede llamarse 'carrera' o el antiguo 'profesorado'
            lt.carrera = pick(["academia_core_carrera", "carrera", "profesorado"])
        if not lt.planes:
            lt.planes = pick(["academia_core_planestudios", "planestudios", "plan_estudios"])
        if not lt.materias:
            lt.materias = pick(["academia_core_materia", "materia"])
        if not lt.join_plan_materia:
            # Puede estar en core o en horarios
            lt.join_plan_materia = pick([
                "academia_core_espaciocurricular",
                "espaciocurricular",
                "academia_horarios_materiaenplan",
                "materiaenplan",
            ])

        return lt

    # ----- carga/insert -------

    def _load_carreras(
        self, cursor, table: str, limit: int
    ) -> Tuple[List[Dict[str, Any]], Dict[int, Carrera], int, int]:
        cols = self._show_columns(cursor, table)
        id_col = _first_present(cols, "id", "pk")
        name_col = _first_present(cols, "nombre", "name", "titulo", "descripcion")
        abbr_col = _first_present(cols, "abreviatura", "shortname", "codigo")

        if not id_col or not name_col:
            raise RuntimeError(
                f"No pude detectar columnas para {table}. Necesito al menos ID y NOMBRE."
            )

        sql = f"SELECT `{id_col}` AS id, `{name_col}` AS nombre"
        if abbr_col:
            sql += f", `{abbr_col}` AS abreviatura"
        sql += f" FROM `{table}`"
        if limit > 0:
            sql += f" LIMIT {limit}"

        rows = self._fetchall(cursor, sql)
        idmap: Dict[int, Carrera] = {}
        created = existed = 0

        for r in rows:
            nombre = _fmt(r["nombre"] or "")
            if not nombre:
                continue
            obj, was_created = Carrera.objects.get_or_create(nombre=nombre)
            if was_created:
                created += 1
            else:
                existed += 1
            # Solo setear abreviatura si el modelo la tiene
            abbr = _fmt((r.get("abreviatura") or "")).upper()[:12] if r.get("abreviatura") else ""
            if abbr:
                try:
                    if getattr(obj, "abreviatura", None) != abbr:
                        obj.abreviatura = abbr
                        obj.save(update_fields=["abreviatura"])
                except Exception:
                    pass
            idmap[int(r["id"])] = obj

        return rows, idmap, created, existed

    def _load_materias(
        self, cursor, table: str, limit: int
    ) -> Tuple[List[Dict[str, Any]], Dict[int, Materia], int, int]:
        cols = self._show_columns(cursor, table)
        id_col = _first_present(cols, "id", "pk")
        name_col = _first_present(cols, "nombre", "name", "titulo", "descripcion")
        if not id_col or not name_col:
            raise RuntimeError(f"No pude detectar columnas para {table} (Materias).")

        sql = f"SELECT `{id_col}` AS id, `{name_col}` AS nombre FROM `{table}`"
        if limit > 0:
            sql += f" LIMIT {limit}"

        rows = self._fetchall(cursor, sql)
        idmap: Dict[int, Materia] = {}
        created = existed = 0

        for r in rows:
            nombre = _fmt(r["nombre"] or "")
            if not nombre:
                continue
            obj, was_created = Materia.objects.get_or_create(nombre=nombre)
            if was_created:
                created += 1
            else:
                existed += 1
            idmap[int(r["id"])] = obj

        return rows, idmap, created, existed

    def _load_planes(
        self, cursor, table: str, limit: int, carrera_idmap: Dict[int, Carrera]
    ) -> Tuple[List[Dict[str, Any]], Dict[int, PlanEstudios], int, int]:
        cols = self._show_columns(cursor, table)
        id_col = _first_present(cols, "id", "pk")
        # FK a carrera/profesorado
        carrera_fk = _first_present(cols, "carrera_id", "profesorado_id")
        resol_col = _first_present(cols, "resolucion", "resolucion_text", "codigo", "nombre", "titulo")

        if not id_col:
            raise RuntimeError(f"No pude detectar columna ID en {table} (Planes).")

        # Seleccionar columnas mínimas
        select_cols = [f"`{id_col}` AS id"]
        if carrera_fk:
            select_cols.append(f"`{carrera_fk}` AS carrera_id")
        if resol_col:
            select_cols.append(f"`{resol_col}` AS resolucion")

        sql = f"SELECT {', '.join(select_cols)} FROM `{table}`"
        if limit > 0:
            sql += f" LIMIT {limit}"

        rows = self._fetchall(cursor, sql)
        idmap: Dict[int, PlanEstudios] = {}
        created = existed = 0

        for r in rows:
            resol = _fmt((r.get("resolucion") or "").strip())
            carrera_obj = None
            if "carrera_id" in r and r["carrera_id"] is not None:
                carrera_obj = carrera_idmap.get(int(r["carrera_id"]))
            defaults = {}
            # Si el modelo tiene 'vigente', setear True por defecto
            try:
                PlanEstudios._meta.get_field("vigente")
                defaults["vigente"] = True
            except Exception:
                pass

            if carrera_obj:
                obj, was_created = PlanEstudios.objects.get_or_create(
                    carrera=carrera_obj, resolucion=resol or "", defaults=defaults
                )
            else:
                # fallback por resolucion sola
                obj, was_created = PlanEstudios.objects.get_or_create(
                    resolucion=resol or "", defaults=defaults
                )

            if was_created:
                created += 1
            else:
                existed += 1

            idmap[int(r["id"])] = obj

        return rows, idmap, created, existed

    def _load_join(
        self,
        cursor,
        table: str,
        limit: int,
        plan_idmap: Dict[int, PlanEstudios],
        materia_idmap: Dict[int, Materia],
    ) -> Tuple[int, int, int]:
        cols = self._show_columns(cursor, table)
        # Detectar columnas FK
        plan_fk = _first_present(cols, "plan_id", "planestudios_id", "plan_id_id", "plan_estudios_id")
        mat_fk = _first_present(cols, "materia_id", "espacio_id", "materia_id_id", "espacio_curricular_id")

        if not plan_fk or not mat_fk:
            # En horarios.materiaenplan suelen ser "plan_id" y "materia_id"
            raise RuntimeError(
                f"No pude detectar FKs (plan/materia) en {table}. Columnas: {cols}"
            )

        sql = f"SELECT `{plan_fk}` AS plan_id, `{mat_fk}` AS materia_id FROM `{table}`"
        if limit > 0:
            sql += f" LIMIT {limit}"

        rows = self._fetchall(cursor, sql)
        created = existed = skipped = 0

        for r in rows:
            pid = r.get("plan_id")
            mid = r.get("materia_id")
            if pid is None or mid is None:
                skipped += 1
                continue
            plan = plan_idmap.get(int(pid))
            mat = materia_idmap.get(int(mid))
            if not plan or not mat:
                skipped += 1
                continue
            obj, was_created = EspacioCurricular.objects.get_or_create(plan=plan, materia=mat)
            if was_created:
                created += 1
            else:
                existed += 1

        return created, existed, skipped

    # ----- main -------

    def handle(self, *args, **options):
        commit: bool = options["commit"]
        limit: int = int(options.get("limit") or 0)
        skip_espacios: bool = options.get("skip_espacios", False)

        forced = LegacyTables(
            carrera=options.get("carrera_table"),
            planes=options.get("planes_table"),
            materias=options.get("materias_table"),
            join_plan_materia=options.get("join_table"),
        )

        self.stdout.write(bold("== Migración legacy: inicio =="))

        with legacy_cursor() as cur:
            # Mostrar base y tablas
            cur.execute("SELECT DATABASE()")
            legacy_db = cur.fetchone()[0]
            self.stdout.write(f"Conectado a legacy DB = {green(repr(legacy_db))}")

            all_tables = self._show_tables(cur)
            self.stdout.write("Tablas detectadas: " + ", ".join(all_tables))

            # Resolver tablas
            tables = self._guess_tables(all_tables, forced)

            def chk(name, value):
                if value:
                    self.stdout.write(f"{name}: {green(value)}")
                else:
                    self.stdout.write(f"{name}: {red('NO ENCONTRADA')}")

            chk("Tabla carreras/profesorados", tables.carrera)
            chk("Tabla planes", tables.planes)
            chk("Tabla materias", tables.materias)
            if not skip_espacios:
                chk("Tabla join plan↔materia", tables.join_plan_materia)

            if not all([tables.carrera, tables.planes, tables.materias]):
                self.stdout.write(red("\nFaltan tablas mínimas (carrera/planes/materias). Abortando.\n"))
                return

            def do_work():
                rows_carreras, idmap_carr, c_new, c_old = self._load_carreras(cur, tables.carrera, limit)
                rows_mats, idmap_mat, m_new, m_old = self._load_materias(cur, tables.materias, limit)
                rows_plans, idmap_plan, p_new, p_old = self._load_planes(cur, tables.planes, limit, idmap_carr)

                e_new = e_old = e_skip = 0
                if not skip_espacios and tables.join_plan_materia:
                    e_new, e_old, e_skip = self._load_join(cur, tables.join_plan_materia, limit, idmap_plan, idmap_mat)

                # Resumen
                self.stdout.write("\n" + bold("== Resumen =="))
                self.stdout.write(f"Carreras: {c_new} nuevas, {c_old} existentes (total legacy: {len(rows_carreras)})")
                self.stdout.write(f"Planes:   {p_new} nuevas, {p_old} existentes (total legacy: {len(rows_plans)})")
                self.stdout.write(f"Materias: {m_new} nuevas, {m_old} existentes (total legacy: {len(rows_mats)})")
                if not skip_espacios and tables.join_plan_materia:
                    self.stdout.write(
                        f"Espacios (join): {e_new} nuevos, {e_old} existentes, {e_skip} saltados"
                    )
                self.stdout.write("")

            if commit:
                self.stdout.write(yellow("Commit: ON (se aplicarán cambios)\n"))
                with transaction.atomic():
                    do_work()
            else:
                self.stdout.write(yellow("Commit: OFF (dry-run)\n"))
                do_work()

        self.stdout.write(bold("== Migración legacy: fin =="))
