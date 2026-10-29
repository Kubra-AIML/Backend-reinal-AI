import hashlib
import json

from app.config import settings
from app.services import replay
from app.services.fixtures import load_fixture

JPEG_HEAD = b"\xff\xd8\xff\xe0"


def upload(client, data):
    return client.post("/api/cases", files={"file": ("eye.jpg", data, "image/jpeg")})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_entry(folder, data, fixture="grade2", engine="cache", raw=None):
    entry = load_fixture(fixture).model_dump(mode="json")
    entry["engine"] = engine
    entry["notice"] = "SYNTHETIC replay fixture for tests. Not a real model output."
    path = folder / f"{sha(data)}.json"
    path.write_text(raw if raw is not None else json.dumps(entry), encoding="utf-8")


def use_cache(monkeypatch, folder):
    monkeypatch.setattr(settings, "engine_mode", "cache")
    monkeypatch.setattr(settings, "replay_dir", folder)


def test_cache_hit_returns_labelled_replay(client, monkeypatch, tmp_path):
    data = JPEG_HEAD + b"known-image"
    write_entry(tmp_path, data)
    use_cache(monkeypatch, tmp_path)
    body = upload(client, data).json()
    assert body["engine"] == "cache"
    assert body["result"]["engine"] == "cache"
    assert "REPLAY" in body["result"]["notice"]
    assert "SYNTHETIC" in body["result"]["notice"]
    assert body["result"]["case_ref"] == body["case_ref"]
    assert body["result"]["prediction"]["grade"] == 2


def test_cache_miss_falls_back_to_labelled_stub(client, monkeypatch, tmp_path):
    use_cache(monkeypatch, tmp_path)
    body = upload(client, JPEG_HEAD + b"unknown-image").json()
    assert body["engine"] == "stub"
    assert "STUB" in body["result"]["notice"]


def test_stub_mode_ignores_replay_entries(client, monkeypatch, tmp_path):
    data = JPEG_HEAD + b"known-image-2"
    write_entry(tmp_path, data)
    monkeypatch.setattr(settings, "replay_dir", tmp_path)
    assert upload(client, data).json()["engine"] == "stub"


def test_replayed_case_is_stored_and_filterable_as_cache(client, monkeypatch, tmp_path):
    data = JPEG_HEAD + b"known-image-3"
    write_entry(tmp_path, data)
    use_cache(monkeypatch, tmp_path)
    upload(client, data)
    assert client.get("/api/cases?engine=cache").json()["total"] == 1
    assert client.get("/api/cases?engine=stub").json()["total"] == 0


def test_entry_claiming_stub_engine_is_rejected(client, monkeypatch, tmp_path):
    data = JPEG_HEAD + b"bad-engine"
    write_entry(tmp_path, data, engine="stub")
    use_cache(monkeypatch, tmp_path)
    r = upload(client, data)
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "replay_entry_invalid"


def test_entry_claiming_matlab_engine_is_rejected(client, monkeypatch, tmp_path):
    data = JPEG_HEAD + b"bad-engine-2"
    write_entry(tmp_path, data, engine="matlab")
    use_cache(monkeypatch, tmp_path)
    r = upload(client, data)
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "replay_entry_invalid"


def test_corrupt_entry_gives_clear_error_and_no_case(client, monkeypatch, tmp_path):
    data = JPEG_HEAD + b"corrupt"
    write_entry(tmp_path, data, raw="{not json")
    use_cache(monkeypatch, tmp_path)
    assert upload(client, data).status_code == 500
    assert client.get("/api/cases").json()["total"] == 0


def test_unusable_replay_entry_keeps_no_prediction(client, monkeypatch, tmp_path):
    data = JPEG_HEAD + b"unusable-replay"
    write_entry(tmp_path, data, fixture="unusable_blurry")
    use_cache(monkeypatch, tmp_path)
    result = upload(client, data).json()["result"]
    assert result["prediction"] is None


def test_matlab_mode_is_not_available(client, monkeypatch):
    monkeypatch.setattr(settings, "engine_mode", "matlab")
    r = upload(client, JPEG_HEAD + b"x")
    assert r.status_code == 501
    assert r.json()["error"]["code"] == "engine_not_available"
    assert client.get("/api/cases").json()["total"] == 0


def test_unknown_engine_mode_is_an_error(client, monkeypatch):
    monkeypatch.setattr(settings, "engine_mode", "banana")
    assert upload(client, JPEG_HEAD + b"y").status_code == 500


def test_lookup_ignores_malformed_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "replay_dir", tmp_path)
    assert replay.lookup("../../etc/passwd", "RG-1") is None
    assert replay.lookup("A" * 64, "RG-1") is None