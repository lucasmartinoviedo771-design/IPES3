import pytest
from model_bakery import baker


@pytest.mark.django_db
def test_carrera_creada_con_bakery():
    carrera = baker.make("academia_core.Carrera", abreviatura="PM")
    assert carrera.pk
