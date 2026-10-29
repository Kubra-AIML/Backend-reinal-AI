import json

from app.config import settings


def setup(monkeypatch, tmp_path, name, data, schema=None, raw_schema=None):
    monkeypatch.setattr(settings, "evidence_dir", tmp_path)
    (tmp_path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    if schema is not None or raw_schema is not None:
        (tmp_path / "schemas").mkdir(exist_ok=True)
        text = raw_schema if raw_schema is not None else json.dumps(schema)
        (tmp_path / "schemas" / f"{name}.schema.json").write_text(text, encoding="utf-8")


SCHEMA = {
    "type": "object",
    "required": ["version", "items"],
    "properties": {"version": {"type": "string"}, "items": {"type": "array"}},
}


def test_json_array_is_rejected(client, monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, "evaluation_summary", [1, 2, 3])
    r = client.get("/api/evidence/evaluation_summary")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "evidence_invalid"


def test_file_without_schema_is_served_when_object(client, monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, "operating_points", {"anything": 1})
    assert client.get("/api/evidence/operating_points").json() == {"anything": 1}


def test_file_matching_schema_is_served(client, monkeypatch, tmp_path):
    good = {"version": "1", "items": []}
    setup(monkeypatch, tmp_path, "robustness_checks", good, schema=SCHEMA)
    r = client.get("/api/evidence/robustness_checks")
    assert r.status_code == 200
    assert r.json() == good


def test_file_not_matching_schema_is_rejected_with_details(client, monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, "robustness_checks", {"version": 5}, schema=SCHEMA)
    r = client.get("/api/evidence/robustness_checks")
    assert r.status_code == 500
    err = r.json()["error"]
    assert err["code"] == "evidence_invalid"
    assert err["details"]


def test_malformed_schema_gives_clear_error(client, monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, "explanation_checks", {"a": 1}, raw_schema="{not json")
    r = client.get("/api/evidence/explanation_checks")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "evidence_schema_invalid"