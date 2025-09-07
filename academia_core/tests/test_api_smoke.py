import pytest


@pytest.mark.django_db
def test_api_planes(client, admin_user):
    client.force_login(admin_user)
    resp = client.get("/api/planes/")
    assert resp.status_code in (200, 204)


@pytest.mark.django_db
def test_api_materias(client, admin_user):
    client.force_login(admin_user)
    resp = client.get("/api/materias/")
    assert resp.status_code in (200, 204)
