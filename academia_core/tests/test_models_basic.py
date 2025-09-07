import pytest


@pytest.mark.django_db
def test_carrera_str(carrera):
    assert str(carrera) == "Profesorado de Matemática"
    assert carrera.abreviatura == "PM"
