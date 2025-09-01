from django.db import migrations

def ensure_coreperms(apps, schema_editor):
    """
    Crea la tabla academia_core_coreperms si no existe.
    Portátil para MySQL / SQLite / Postgres.
    """
    conn = schema_editor.connection
    vendor = conn.vendor

    with conn.cursor() as c:
        exists = False

        if vendor == "mysql":
            c.execute("SHOW TABLES LIKE 'academia_core_coreperms'")
            exists = c.fetchone() is not None
            if not exists:
                c.execute("""
                    CREATE TABLE `academia_core_coreperms` (
                        `id` BIGINT NOT NULL AUTO_INCREMENT,
                        PRIMARY KEY (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)

        elif vendor == "sqlite":
            c.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='academia_core_coreperms'
            """)
            exists = c.fetchone() is not None
            if not exists:
                c.execute("""
                    CREATE TABLE "academia_core_coreperms" (
                        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT
                    );
                """)

        else:  # postgres y otros
            # Postgres: to_regclass devuelve None si no existe
            c.execute("SELECT to_regclass('public.academia_core_coreperms')")
            exists = (c.fetchone() or [None])[0] is not None
            if not exists:
                c.execute("""
                    CREATE TABLE academia_core_coreperms (
                        id BIGSERIAL PRIMARY KEY
                    );
                """)

def drop_coreperms(apps, schema_editor):
    """Reverse: borrar la tabla si existe (opcional)."""
    conn = schema_editor.connection
    vendor = conn.vendor

    with conn.cursor() as c:
        if vendor == "mysql":
            c.execute("DROP TABLE IF EXISTS `academia_core_coreperms`")
        elif vendor == "sqlite":
            c.execute("DROP TABLE IF EXISTS academia_core_coreperms")
        else:  # postgres
            c.execute("DROP TABLE IF EXISTS academia_core_coreperms")


class Migration(migrations.Migration):
    # Que corra luego de 0005 (donde se introdujo el modelo)
    dependencies = [
        ("academia_core", "0005_coreperms"),
    ]

    operations = [
        migrations.RunPython(ensure_coreperms, drop_coreperms),
    ]
