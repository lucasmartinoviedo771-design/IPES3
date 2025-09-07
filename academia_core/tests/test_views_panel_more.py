import pytest


@pytest.mark.django_db
def test_cargar_horario_requires_login(client):
    resp = client.get("/panel/horarios/cargar/")
    assert resp.status_code in (302, 401, 403)


@pytest.mark.django_db
def test_cargar_horario_ok(client, admin_user):
    client.force_login(admin_user)
    resp = client.get("/panel/horarios/cargar/")
    assert resp.status_code == 200
    assert b"Armar Horarios" in resp.content
