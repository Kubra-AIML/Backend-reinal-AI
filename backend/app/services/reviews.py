from typing import Optional

from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models import Case, Review
from .audit import record_event


def add_review(
    db: Session,
    *,
    case_id: str,
    reviewer: str,
    decision: str,
    corrected_grade: Optional[int] = None,
    notes: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Review:
    """Always INSERTS a new review. The original prediction on the case is never touched."""
    case = db.get(Case, case_id)
    if case is None:
        raise ApiError(404, "not_found", "Case not found")
    if corrected_grade is not None and not (0 <= corrected_grade <= 4):
        raise ApiError(422, "validation_error", "corrected_grade must be between 0 and 4")

    review = Review(
        case_id=case_id,
        reviewer=reviewer,
        decision=decision,
        corrected_grade=corrected_grade,
        notes=notes,
    )
    db.add(review)
    db.flush()
    record_event(
        db,
        "review_added",
        case_id=case_id,
        actor=reviewer,
        request_id=request_id,
        details={"review_id": review.id, "decision": decision, "corrected_grade": corrected_grade},
    )
    return review