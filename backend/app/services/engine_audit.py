import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditEvent
from .audit import record_event


def record_engine_mode_if_changed(db: Session, mode: str) -> bool:
    """Appends an engine_mode_changed event when the mode differs from the last recorded one."""
    last = db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "engine_mode_changed").order_by(AuditEvent.id.desc())
    ).first()
    previous = None
    if last is not None and last.details_json:
        previous = json.loads(last.details_json).get("to")
    if previous == mode:
        return False
    record_event(db, "engine_mode_changed", actor="system", details={"from": previous, "to": mode})
    db.commit()
    return True