import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_panel_horarios_requires_login(client):
    url = reverse("academia_horarios:cargar_horario")
    resp = client.get(url)
    assert resp.status_code in (302, 401, 403)


@pytest.mark.django_db
def test_panel_horarios_ok_logged_in(client, admin_user):
    client.force_login(admin_user)
    url = reverse("academia_horarios:cargar_horario")
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Armar Horarios" in resp.content
