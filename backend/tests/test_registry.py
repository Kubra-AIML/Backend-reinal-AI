import json

from app.config import settings

VALID = {
    "registry_version": "1",
    "active": "m2",
    "models": [
        {"id": "m1", "classifier": "c1", "quality_gate": "q1", "preprocess_spec": "p1"},
        {
            "id": "m2",
            "classifier": "c2",
            "quality_gate": "q2",
            "preprocess_spec": "p2",
            "dataset_split": "split-a",
            "run_id": "run-42",
            "attribution_method_version": "gradcam-1",
        },
    ],
}


def write(tmp_path, monkeypatch, data, raw=None):
    path = tmp_path / "registry.json"
    path.write_text(raw if raw is not None else json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(settings, "registry_path", path)
    return path


def test_registry_not_ready_is_clear_404(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "registry_path", tmp_path / "missing.json")
    for path in ("/api/models", "/api/models/active"):
        r = client.get(path)
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "registry_not_ready"


def test_active_model_is_returned(client, monkeypatch, tmp_path):
    write(tmp_path, monkeypatch, VALID)
    body = client.get("/api/models/active").json()
    assert body["registry_version"] == "1"
    assert body["model"]["id"] == "m2"
    assert body["model"]["run_id"] == "run-42"


def test_full_registry_is_listed(client, monkeypatch, tmp_path):
    write(tmp_path, monkeypatch, VALID)
    body = client.get("/api/models").json()
    assert [m["id"] for m in body["models"]] == ["m1", "m2"]


def test_registry_file_is_never_modified(client, monkeypatch, tmp_path):
    path = write(tmp_path, monkeypatch, VALID)
    before = path.read_bytes()
    client.get("/api/models")
    client.get("/api/models/active")
    assert path.read_bytes() == before


def test_invalid_json_gives_clear_error(client, monkeypatch, tmp_path):
    write(tmp_path, monkeypatch, None, raw="{not json")
    r = client.get("/api/models/active")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "registry_invalid"


def test_active_must_exist_in_models(client, monkeypatch, tmp_path):
    write(tmp_path, monkeypatch, {**VALID, "active": "ghost"})
    assert client.get("/api/models/active").status_code == 500


def test_duplicate_ids_rejected(client, monkeypatch, tmp_path):
    dup = {**VALID, "models": [VALID["models"][0], VALID["models"][0]], "active": "m1"}
    write(tmp_path, monkeypatch, dup)
    assert client.get("/api/models").status_code == 500