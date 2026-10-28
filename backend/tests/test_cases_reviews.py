import hashlib

import pytest

from app.services.audit import list_events
from app.services.engine_stub import pick_fixture_name

JPEG_HEAD = b"\xff\xd8\xff\xe0"


def jpeg(tag):
    return JPEG_HEAD + f"payload-{tag}".encode()


def upload(client, data):
    return client.post("/api/cases", files={"file": ("eye.jpg", data, "image/jpeg")})


def payload_for(fixture_name):
    for i in range(2000):
        data = JPEG_HEAD + f"probe-{i}".encode()
        if pick_fixture_name(hashlib.sha256(data).hexdigest()) == fixture_name:
            return data
    raise AssertionError("no payload found")


def test_list_empty(client):
    r = client.get("/api/cases")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_list_is_newest_first_and_paged(client):
    refs = [upload(client, jpeg(i)).json()["case_ref"] for i in range(3)]
    full = client.get("/api/cases").json()
    assert full["total"] == 3
    assert [c["case_ref"] for c in full["items"]] == list(reversed(refs))

    page1 = client.get("/api/cases?limit=2&offset=0").json()
    page2 = client.get("/api/cases?limit=2&offset=2").json()
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 1
    assert page2["items"][0]["case_ref"] == refs[0]


def test_list_rejects_bad_paging(client):
    r = client.get("/api/cases?limit=0")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_list_engine_filter(client):
    upload(client, jpeg("f"))
    assert client.get("/api/cases?engine=stub").json()["total"] == 1
    assert client.get("/api/cases?engine=matlab").json()["total"] == 0


def test_summary_for_unusable_case_has_no_grade(client):
    upload(client, payload_for("unusable_blurry"))
    item = client.get("/api/cases").json()["items"][0]
    assert item["quality_verdict"] == "unusable"
    assert item["grade"] is None
    assert item["referable"] is None
    assert item["review_flags"]


def test_detail_by_id_and_by_case_ref(client):
    created = upload(client, jpeg("detail")).json()
    by_id = client.get(f"/api/cases/{created['id']}")
    by_ref = client.get(f"/api/cases/{created['case_ref']}")
    assert by_id.status_code == 200
    assert by_ref.status_code == 200
    assert by_id.json()["id"] == by_ref.json()["id"] == created["id"]
    assert by_id.json()["reviews"] == []
    assert by_id.json()["result"]["engine"] == "stub"


def test_detail_unknown_case_is_404(client):
    r = client.get("/api/cases/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_review_agree_is_created_and_shown_in_detail(client):
    case = upload(client, jpeg("rev1")).json()
    r = client.post(f"/api/cases/{case['case_ref']}/reviews", json={"reviewer": "dr_a", "decision": "agree"})
    assert r.status_code == 201
    body = r.json()
    assert body["decision"] == "agree"
    assert body["case_ref"] == case["case_ref"]
    detail = client.get(f"/api/cases/{case['id']}").json()
    assert len(detail["reviews"]) == 1


def test_reviews_append_and_original_result_unchanged(client):
    case = upload(client, jpeg("rev2")).json()
    before = client.get(f"/api/cases/{case['id']}").json()["result"]
    client.post(f"/api/cases/{case['id']}/reviews", json={"reviewer": "dr_a", "decision": "agree"})
    client.post(
        f"/api/cases/{case['id']}/reviews",
        json={"reviewer": "dr_b", "decision": "override", "corrected_grade": 3, "notes": "second opinion"},
    )
    detail = client.get(f"/api/cases/{case['id']}").json()
    assert detail["result"] == before
    assert [r["decision"] for r in detail["reviews"]] == ["agree", "override"]
    assert detail["reviews"][1]["corrected_grade"] == 3


def test_override_requires_corrected_grade(client):
    case = upload(client, jpeg("rev3")).json()
    r = client.post(f"/api/cases/{case['id']}/reviews", json={"reviewer": "dr_a", "decision": "override"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_agree_must_not_carry_corrected_grade(client):
    case = upload(client, jpeg("rev4")).json()
    r = client.post(
        f"/api/cases/{case['id']}/reviews",
        json={"reviewer": "dr_a", "decision": "agree", "corrected_grade": 2},
    )
    assert r.status_code == 422


def test_corrected_grade_out_of_range_rejected(client):
    case = upload(client, jpeg("rev5")).json()
    r = client.post(
        f"/api/cases/{case['id']}/reviews",
        json={"reviewer": "dr_a", "decision": "override", "corrected_grade": 9},
    )
    assert r.status_code == 422


def test_unknown_decision_rejected(client):
    case = upload(client, jpeg("rev6")).json()
    r = client.post(f"/api/cases/{case['id']}/reviews", json={"reviewer": "dr_a", "decision": "approve_all"})
    assert r.status_code == 422


def test_review_for_unknown_case_is_404(client):
    r = client.post("/api/cases/nope/reviews", json={"reviewer": "dr_a", "decision": "agree"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_review_creates_audit_event(client, session_factory):
    case = upload(client, jpeg("rev7")).json()
    client.post(f"/api/cases/{case['id']}/reviews", json={"reviewer": "dr_a", "decision": "agree"})
    with session_factory() as s:
        types = [e.event_type for e in list_events(s, case_id=case["id"])]
    assert types == ["upload_received", "analysis_requested", "review_added"]