import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditEvent

EVENT_TYPES = frozenset(
    {
        "upload_received",
        "duplicate_upload_detected",
        "analysis_requested",
        "review_added",
        "report_downloaded",
        "engine_mode_changed",
    }
)

# NOTE: this module intentionally offers no update or delete function.


def record_event(
    db: Session,
    event_type: str,
    *,
    case_id: Optional[str] = None,
    actor: str = "system",
    request_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    """Add one audit event. The caller commits. Never put patient-identifying data in details."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown audit event type: {event_type}")
    event = AuditEvent(
        event_type=event_type,
        case_id=case_id,
        actor=actor,
        request_id=request_id,
        details_json=json.dumps(details, sort_keys=True) if details is not None else None,
    )
    db.add(event)
    db.flush()
    return event


def list_events(db: Session, *, case_id: Optional[str] = None, limit: int = 100) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.id.asc()).limit(limit)
    if case_id is not None:
        stmt = stmt.where(AuditEvent.case_id == case_id)
    return list(db.scalars(stmt).all())