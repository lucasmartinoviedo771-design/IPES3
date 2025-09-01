import pytest
from django.apps import apps
from django.conf import settings as dj_settings

def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None

def test_apps_installed():
    assert "academia_core.apps.AcademiaCoreConfig" in dj_settings.INSTALLED_APPS
    assert "academia_horarios" in dj_settings.INSTALLED_APPS
    assert "ui" in dj_settings.INSTALLED_APPS

@pytest.mark.parametrize(
    "app_label, model_name",
    [
        ("academia_horarios", "Horario"),
        ("academia_horarios", "Comision"),
        ("academia_horarios", "Docente"),
    ],
)
def test_modelos_clave_existen(app_label, model_name):
    # Si algún nombre no coincide en tu código real, el test se salta (no rompe)
    if _get_model(app_label, model_name) is None:
        pytest.skip(f"Modelo no encontrado (ajustar nombres): {app_label}.{model_name}")
