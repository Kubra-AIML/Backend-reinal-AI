import json

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DatabaseError

from app.errors import ApiError
from app.models import AppendOnlyError, Case, Review
from app.schemas.result import Versions
from app.services.audit import list_events, record_event
from app.services.fixtures import load_fixture
from app.services.model_versions import get_or_create_model_version
from app.services.reviews import add_review

VERSIONS = Versions(classifier="c1", quality_gate="q1", preprocess_spec="p1")


def make_case(db):
    mv = get_or_create_model_version(db, VERSIONS, "stub")
    result = load_fixture("grade2")
    case = Case(
        case_ref="RG-TEST0001",
        image_sha256="a" * 64,
        content_type="image/jpeg",
        size_bytes=1234,
        engine="stub",
        model_version_id=mv.id,
        result_json=result.model_dump_json(),
    )
    db.add(case)
    db.commit()
    return case


def test_migration_creates_all_tables(db):
    names = set(inspect(db.get_bind()).get_table_names())
    assert {"cases", "reviews", "audit_events", "model_versions"} <= names


def test_model_version_is_reused(db):
    a = get_or_create_model_version(db, VERSIONS, "stub")
    b = get_or_create_model_version(db, VERSIONS, "stub")
    assert a.id == b.id


def test_audit_event_is_recorded_and_listed(db):
    case = make_case(db)
    record_event(db, "upload_received", case_id=case.id, request_id="r1", details={"size": 1234})
    db.commit()
    events = list_events(db, case_id=case.id)
    assert len(events) == 1
    assert events[0].event_type == "upload_received"
    assert json.loads(events[0].details_json) == {"size": 1234}


def test_unknown_audit_event_type_rejected(db):
    with pytest.raises(ValueError):
        record_event(db, "something_made_up")


def test_audit_event_cannot_be_changed_via_orm(db):
    ev = record_event(db, "upload_received")
    db.commit()
    ev.actor = "someone_else"
    with pytest.raises(AppendOnlyError):
        db.commit()
    db.rollback()


def test_audit_event_cannot_be_updated_in_database(db):
    record_event(db, "upload_received")
    db.commit()
    with pytest.raises(DatabaseError):
        db.execute(text("UPDATE audit_events SET actor = 'x'"))
    db.rollback()


def test_audit_event_cannot_be_deleted_in_database(db):
    record_event(db, "upload_received")
    db.commit()
    with pytest.raises(DatabaseError):
        db.execute(text("DELETE FROM audit_events"))
    db.rollback()


def test_review_is_additive_and_original_prediction_untouched(db):
    case = make_case(db)
    original = case.result_json
    r1 = add_review(db, case_id=case.id, reviewer="dr_a", decision="agree")
    r2 = add_review(db, case_id=case.id, reviewer="dr_b", decision="override", corrected_grade=3, notes="x")
    db.commit()
    db.refresh(case)

    assert case.result_json == original
    assert json.loads(case.result_json)["prediction"]["grade"] == 2
    reviews = db.scalars(select(Review).where(Review.case_id == case.id)).all()
    assert len(reviews) == 2
    assert r1.id != r2.id
    assert [e.event_type for e in list_events(db, case_id=case.id)] == ["review_added", "review_added"]


def test_review_cannot_be_updated_in_database(db):
    case = make_case(db)
    add_review(db, case_id=case.id, reviewer="dr_a", decision="agree")
    db.commit()
    with pytest.raises(DatabaseError):
        db.execute(text("UPDATE reviews SET decision = 'changed'"))
    db.rollback()


def test_case_result_cannot_be_overwritten_in_database(db):
    make_case(db)
    with pytest.raises(DatabaseError):
        db.execute(text("UPDATE cases SET result_json = '{}'"))
    db.rollback()


def test_case_result_cannot_be_overwritten_via_orm(db):
    case = make_case(db)
    case.result_json = "{}"
    with pytest.raises(AppendOnlyError):
        db.commit()
    db.rollback()


def test_review_for_unknown_case_is_404(db):
    with pytest.raises(ApiError) as exc:
        add_review(db, case_id="nope", reviewer="dr_a", decision="agree")
    assert exc.value.status_code == 404


def test_review_with_bad_grade_rejected(db):
    case = make_case(db)
    with pytest.raises(ApiError) as exc:
        add_review(db, case_id=case.id, reviewer="dr_a", decision="override", corrected_grade=9)
    assert exc.value.status_code == 422