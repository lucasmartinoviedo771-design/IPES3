import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_api_timeslots_requires_login(client):
    url = reverse("academia_horarios:api_timeslots")
    resp = client.get(url)
    assert resp.status_code in (302, 401, 403)


@pytest.mark.django_db
def test_api_timeslots_maniana_ok(client, admin_user):
    client.force_login(admin_user)
    url = reverse("academia_horarios:api_timeslots") + "?turno=maniana"
    resp = client.get(url)
    assert resp.status_code == 200
    assert "lv" in resp.json()
    assert "sab" in resp.json()


@pytest.mark.django_db
def test_api_timeslots_invalid_turno_defaults_to_maniana(client, admin_user):
    client.force_login(admin_user)
    url = reverse("academia_horarios:api_timeslots") + "?turno=invalid"
    resp = client.get(url)
    assert resp.status_code == 200
    # Based on the view logic, an invalid turno defaults to 'maniana'
    # So we expect the 'maniana' timeslots
    assert "lv" in resp.json()
    assert "sab" in resp.json()
