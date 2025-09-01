from django.apps import AppConfig


class AcademiaHorariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "academia_horarios"

    def ready(self):
        # importa signals para que se registren
        from . import signals  # noqa
