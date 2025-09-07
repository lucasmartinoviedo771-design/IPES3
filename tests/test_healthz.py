def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert b"ok" in r.content
