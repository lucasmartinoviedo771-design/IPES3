import pytest


@pytest.mark.django_db
def test_cargar_horario_requires_login(client):
    r = client.get("/panel/horarios/cargar/")
    assert r.status_code in (302, 401, 403)


@pytest.mark.django_db
def test_cargar_horario_ok(client, django_user_model):
    user = django_user_model.objects.create_superuser("admin", "a@a.com", "pass")
    client.force_login(user)
    r = client.get("/panel/horarios/cargar/")
    assert r.status_code == 200
    assert b"Armar Horarios" in r.content
