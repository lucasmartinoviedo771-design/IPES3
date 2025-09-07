import pytest
from django.contrib.auth import get_user_model

from academia_core.models import Carrera, PlanEstudios


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass"
    )


@pytest.fixture
def carrera(db):
    return Carrera.objects.create(nombre="Profesorado de Matemática", abreviatura="PM")


@pytest.fixture
def plan_estudios(db, carrera):
    return PlanEstudios.objects.create(carrera=carrera, resolucion="1234/2025", nombre="Plan 2025")
