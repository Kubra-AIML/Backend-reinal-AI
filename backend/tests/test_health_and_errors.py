from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_stub_engine():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["api"] == "ok"
    assert body["engine"]["mode"] == "stub"
    assert body["engine"]["live_inference"] is False


def test_unknown_route_uses_standard_error_shape():
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "not_found"
    assert err["message"]
    assert err["request_id"]


def test_request_id_is_echoed_when_supplied():
    r = client.get("/api/does-not-exist", headers={"X-Request-ID": "abc123"})
    assert r.json()["error"]["request_id"] == "abc123"