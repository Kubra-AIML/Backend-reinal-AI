import json

from app.services.audit import list_events
from app.services.engine_audit import record_engine_mode_if_changed


def modes(db):
    return [json.loads(e.details_json) for e in list_events(db) if e.event_type == "engine_mode_changed"]


def test_first_call_records_initial_mode(db):
    assert record_engine_mode_if_changed(db, "stub") is True
    assert modes(db) == [{"from": None, "to": "stub"}]


def test_same_mode_is_not_recorded_twice(db):
    record_engine_mode_if_changed(db, "stub")
    assert record_engine_mode_if_changed(db, "stub") is False
    assert len(modes(db)) == 1


def test_change_is_recorded_with_old_and_new_mode(db):
    record_engine_mode_if_changed(db, "stub")
    record_engine_mode_if_changed(db, "cache")
    assert modes(db) == [{"from": None, "to": "stub"}, {"from": "stub", "to": "cache"}]


def test_startup_records_the_mode(client, session_factory):
    with session_factory() as s:
        assert {"from": None, "to": "stub"} in modes(s)