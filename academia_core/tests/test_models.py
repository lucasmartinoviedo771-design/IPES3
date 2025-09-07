import pytest

from academia_core.models import Carrera


@pytest.mark.django_db
def test_crear_carrera():
    c = Carrera.objects.create(nombre="Prueba", abreviatura="PR")
    assert str(c) == "Prueba"
