from django.conf import settings as dj_settings


def test_django_settings():
    assert dj_settings.ROOT_URLCONF == "academia_project.urls"
    assert "academia_horarios" in dj_settings.INSTALLED_APPS
    assert "academia_core.apps.AcademiaCoreConfig" in dj_settings.INSTALLED_APPS
