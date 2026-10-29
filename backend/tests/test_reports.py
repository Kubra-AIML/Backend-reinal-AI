import hashlib

import pytest

from app.services.audit import list_events
from app.services.engine_stub import pick_fixture_name
from app.services.fixtures import FIXTURE_NAMES

JPEG_HEAD = b"\xff\xd8\xff\xe0"


def upload(client, data):
    return client.post("/api/cases", files={"file": ("eye.jpg", data, "image/jpeg")})


def make_case(client, tag="r"):
    return upload(client, JPEG_HEAD + f"payload-{tag}".encode()).json()


def payload_for(fixture_name):
    for i in range(2000):
        data = JPEG_HEAD + f"probe-{i}".encode()
        if pick_fixture_name(hashlib.sha256(data).hexdigest()) == fixture_name:
            return data
    raise AssertionError("no payload found")


def test_report_json_contains_same_result_as_case(client):
    case = make_case(client)
    r = client.get(f"/api/cases/{case['case_ref']}/report")
    assert r.status_code == 200
    body = r.json()
    assert body["case_ref"] == case["case_ref"]
    assert body["result"] == case["result"]
    assert body["result"]["engine"] == "stub"
    assert body["reviews"] == []


def test_report_has_required_sections(client):
    body = client.get(f"/api/cases/{make_case(client)['id']}/report").json()
    assert body["input_image_available"] is False
    assert body["heatmap"]["available"] is False
    assert "attribution" in body["heatmap"]["label"].lower()
    assert "uncalibrated" in body["confidence_policy"].lower()
    assert body["benchmark_caveat"]
    assert body["limitations_text"]
    assert "clinician" in body["clinician_statement"].lower()
    assert body["clinician_decision_fields"]


def test_report_lists_reviews_and_keeps_original_result(client):
    case = make_case(client, "rv")
    client.post(
        f"/api/cases/{case['id']}/reviews",
        json={"reviewer": "dr_a", "decision": "override", "corrected_grade": 3},
    )
    body = client.get(f"/api/cases/{case['id']}/report").json()
    assert len(body["reviews"]) == 1
    assert body["reviews"][0]["corrected_grade"] == 3
    assert body["result"] == case["result"]


def test_report_for_unusable_case_has_no_prediction(client):
    case = upload(client, payload_for("unusable_blurry")).json()
    body = client.get(f"/api/cases/{case['id']}/report").json()
    assert body["result"]["prediction"] is None


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_pdf_renders_for_every_fixture(client, fixture_name):
    case = upload(client, payload_for(fixture_name)).json()
    r = client.get(f"/api/cases/{case['case_ref']}/report.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")
    assert r.content.rstrip().endswith(b"%%EOF")
    assert len(r.content) > 1500


def test_pdf_download_header_names_the_case(client):
    case = make_case(client, "hdr")
    r = client.get(f"/api/cases/{case['case_ref']}/report.pdf")
    assert case["case_ref"] in r.headers["content-disposition"]


def test_pdf_download_creates_audit_event_but_json_does_not(client, session_factory):
    case = make_case(client, "aud")
    client.get(f"/api/cases/{case['id']}/report")
    with session_factory() as s:
        types = [e.event_type for e in list_events(s, case_id=case["id"])]
    assert "report_downloaded" not in types

    client.get(f"/api/cases/{case['id']}/report.pdf")
    client.get(f"/api/cases/{case['id']}/report.pdf")
    with session_factory() as s:
        types = [e.event_type for e in list_events(s, case_id=case["id"])]
    assert types.count("report_downloaded") == 2


def test_pdf_handles_special_characters_in_review_notes(client):
    case = make_case(client, "xml")
    client.post(
        f"/api/cases/{case['id']}/reviews",
        json={"reviewer": "dr <b>&", "decision": "agree", "notes": "<script>x</script> & <para>"},
    )
    r = client.get(f"/api/cases/{case['id']}/report.pdf")
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")


def test_report_unknown_case_is_404(client):
    for path in ("/api/cases/nope/report", "/api/cases/nope/report.pdf"):
        r = client.get(path)
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "not_found"