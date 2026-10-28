import hashlib

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models import Case
from app.services.audit import list_events
from app.services.engine_stub import pick_fixture_name

JPEG_HEAD = b"\xff\xd8\xff\xe0"
PNG_HEAD = b"\x89PNG\r\n\x1a\n"


def jpeg(tag="a"):
    return JPEG_HEAD + f"payload-{tag}".encode()


def upload(client, data, name="eye.jpg", ctype="image/jpeg", headers=None):
    return client.post("/api/cases", files={"file": (name, data, ctype)}, headers=headers or {})


def count_cases(session_factory):
    with session_factory() as s:
        return s.scalar(select(func.count()).select_from(Case))


def payload_for(fixture_name):
    for i in range(2000):
        data = JPEG_HEAD + f"probe-{i}".encode()
        if pick_fixture_name(hashlib.sha256(data).hexdigest()) == fixture_name:
            return data
    raise AssertionError("no payload found")


def test_jpeg_upload_creates_stub_case(client):
    r = upload(client, jpeg())
    assert r.status_code == 201
    body = r.json()
    assert body["case_ref"].startswith("RG-")
    assert body["content_type"] == "image/jpeg"
    assert body["engine"] == "stub"
    assert body["result"]["engine"] == "stub"
    assert "STUB" in body["result"]["notice"]
    assert body["result"]["case_ref"] == body["case_ref"]
    assert body["idempotent_replay"] is False
    assert body["duplicate_warning"]["is_duplicate"] is False


def test_png_upload_accepted(client):
    r = upload(client, PNG_HEAD + b"data", name="eye.png", ctype="image/png")
    assert r.status_code == 201
    assert r.json()["content_type"] == "image/png"


def test_text_file_named_jpg_is_rejected(client):
    r = upload(client, b"just some text, not an image", name="eye.jpg", ctype="image/jpeg")
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_media_type"


def test_signature_wins_over_extension_and_client_type(client):
    r = upload(client, PNG_HEAD + b"data", name="notes.txt", ctype="text/plain")
    assert r.status_code == 201
    assert r.json()["content_type"] == "image/png"


def test_empty_file_rejected(client):
    r = upload(client, b"")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "empty_file"


def test_oversized_file_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    r = upload(client, JPEG_HEAD + b"0" * (1024 * 1024))
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "payload_too_large"


def test_missing_file_is_validation_error(client):
    r = client.post("/api/cases")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_sha256_is_calculated(client):
    data = jpeg("hash")
    r = upload(client, data)
    assert r.json()["image_sha256"] == hashlib.sha256(data).hexdigest()


def test_duplicate_upload_warns_but_creates_new_case(client, session_factory):
    data = jpeg("dup")
    first = upload(client, data).json()
    second = upload(client, data).json()
    assert second["id"] != first["id"]
    assert second["duplicate_warning"]["is_duplicate"] is True
    assert second["duplicate_warning"]["existing_case_refs"] == [first["case_ref"]]
    assert count_cases(session_factory) == 2


def test_idempotency_key_prevents_duplicate_case(client, session_factory):
    headers = {"Idempotency-Key": "retry-1"}
    first = upload(client, jpeg("idem"), headers=headers)
    second = upload(client, jpeg("idem"), headers=headers)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers["Idempotent-Replay"] == "true"
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["idempotent_replay"] is True
    assert count_cases(session_factory) == 1
    with session_factory() as s:
        events = [e.event_type for e in list_events(s)]
    assert events.count("upload_received") == 1


def test_idempotency_key_reused_with_different_file_conflicts(client, session_factory):
    headers = {"Idempotency-Key": "retry-2"}
    upload(client, jpeg("one"), headers=headers)
    r = upload(client, jpeg("two"), headers=headers)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "idempotency_key_reused"
    assert count_cases(session_factory) == 1


def test_invalid_idempotency_key_rejected(client):
    r = upload(client, jpeg(), headers={"Idempotency-Key": "bad key!"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("fixture_name", ["unusable_blurry", "non_fundus"])
def test_unusable_and_non_fundus_uploads_have_no_prediction(client, fixture_name):
    r = upload(client, payload_for(fixture_name))
    assert r.status_code == 201
    result = r.json()["result"]
    assert result["quality"]["verdict"] != "usable"
    assert result["prediction"] is None
    assert result["review_flags"]


def test_audit_events_for_upload(client, session_factory):
    case_id = upload(client, jpeg("audit")).json()["id"]
    with session_factory() as s:
        types = [e.event_type for e in list_events(s, case_id=case_id)]
    assert types == ["upload_received", "analysis_requested"]


def test_audit_event_for_duplicate(client, session_factory):
    data = jpeg("auditdup")
    upload(client, data)
    case_id = upload(client, data).json()["id"]
    with session_factory() as s:
        types = [e.event_type for e in list_events(s, case_id=case_id)]
    assert types == ["upload_received", "duplicate_upload_detected", "analysis_requested"]