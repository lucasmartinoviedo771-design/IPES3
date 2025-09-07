import os

import django

from academia_core.models import PlanEstudios

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academia_project.settings")
django.setup()

try:
    obj = PlanEstudios.objects.get(pk=14)
    print(f"PlanEstudios with pk=14: {obj.nombre}, Profesorado ID: {obj.profesorado_id}")
except PlanEstudios.DoesNotExist:
    print("PlanEstudios with pk=14 does not exist.")
