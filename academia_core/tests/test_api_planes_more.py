import pytest


@pytest.mark.django_db
def test_api_planes_ok(client, admin_user):
    client.force_login(admin_user)
    r = client.get("/api/planes/")
    assert r.status_code in (200, 204)
