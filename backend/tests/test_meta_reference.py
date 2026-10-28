import json

from app.config import settings
from app.services.fixtures import FIXTURE_NAMES, load_fixture


def test_meta_has_required_fields(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    m = r.json()
    assert m["product_name"] == settings.product_name
    assert m["engine_mode"] == "stub"
    assert m["live_inference"] is False
    assert set(m["versions"]) == {"classifier", "quality_gate", "preprocess_spec"}
    assert m["referable_threshold"] == settings.referable_threshold
    assert "uncalibrated" in m["confidence_policy"].lower()
    assert m["limitations_text"]
    assert "clinician" in m["clinician_statement"].lower()
    assert m["accepted_content_types"] == ["image/jpeg", "image/png"]
    assert "override" in m["review_decisions"]


def test_meta_reads_settings_not_hard_coded_values(client, monkeypatch):
    monkeypatch.setattr(settings, "referable_threshold", 0.7)
    assert client.get("/api/meta").json()["referable_threshold"] == 0.7


def test_reason_codes_are_served(client):
    r = client.get("/api/reason-codes")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "placeholder"
    assert {c["code"] for c in body["reason_codes"]}


def test_every_fixture_reason_code_is_listed(client):
    listed = {c["code"] for c in client.get("/api/reason-codes").json()["reason_codes"]}
    used = set()
    for name in FIXTURE_NAMES:
        used.update(load_fixture(name).quality.reason_codes)
    assert used <= listed


def test_evidence_index_all_not_ready_when_folder_empty(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "evidence_dir", tmp_path)
    files = client.get("/api/evidence").json()["files"]
    assert len(files) == 5
    assert all(f["available"] is False for f in files)


def test_evidence_unknown_name_is_404(client):
    r = client.get("/api/evidence/secrets")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "unknown_evidence"


def test_evidence_not_ready_is_clear_404(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "evidence_dir", tmp_path)
    r = client.get("/api/evidence/evaluation_summary")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "evidence_not_ready"


def test_evidence_file_is_served(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "evidence_dir", tmp_path)
    payload = {"note": "test data", "value": 1}
    (tmp_path / "evaluation_summary.json").write_text(json.dumps(payload), encoding="utf-8")
    r = client.get("/api/evidence/evaluation_summary")
    assert r.status_code == 200
    assert r.json() == payload
    available = {f["name"]: f["available"] for f in client.get("/api/evidence").json()["files"]}
    assert available["evaluation_summary"] is True


def test_evidence_invalid_json_gives_clear_error(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "evidence_dir", tmp_path)
    (tmp_path / "operating_points.json").write_text("{not json", encoding="utf-8")
    r = client.get("/api/evidence/operating_points")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "evidence_invalid"