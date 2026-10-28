from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models import Case, Review
from ..schemas.case import CaseDetail, CaseList, CaseSummary
from ..schemas.result import AnalysisResult
from ..schemas.review import ReviewOut
from .cases import to_response


def as_utc(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; we store UTC.
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def get_case_or_404(db: Session, ref_or_id: str) -> Case:
    case = db.get(Case, ref_or_id)
    if case is None:
        case = db.scalars(select(Case).where(Case.case_ref == ref_or_id)).first()
    if case is None:
        raise ApiError(404, "not_found", "Case not found")
    return case


def review_out(review: Review, case_ref: str) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        case_id=review.case_id,
        case_ref=case_ref,
        reviewer=review.reviewer,
        decision=review.decision,
        corrected_grade=review.corrected_grade,
        notes=review.notes,
        created_at=as_utc(review.created_at),
    )


def list_cases(db: Session, *, limit: int, offset: int, engine: Optional[str]) -> CaseList:
    rows_stmt = select(Case)
    count_stmt = select(func.count()).select_from(Case)
    if engine:
        rows_stmt = rows_stmt.where(Case.engine == engine)
        count_stmt = count_stmt.where(Case.engine == engine)

    total = db.scalar(count_stmt) or 0
    rows = list(
        db.scalars(rows_stmt.order_by(Case.created_at.desc(), Case.id.desc()).limit(limit).offset(offset)).all()
    )

    counts: dict[str, int] = {}
    if rows:
        counts = dict(
            db.execute(
                select(Review.case_id, func.count())
                .where(Review.case_id.in_([c.id for c in rows]))
                .group_by(Review.case_id)
            ).all()
        )

    items = []
    for c in rows:
        result = AnalysisResult.model_validate_json(c.result_json)
        items.append(
            CaseSummary(
                id=c.id,
                case_ref=c.case_ref,
                created_at=as_utc(c.created_at),
                engine=c.engine,
                quality_verdict=result.quality.verdict,
                grade=result.prediction.grade if result.prediction else None,
                referable=result.prediction.referable if result.prediction else None,
                review_flags=result.review_flags,
                review_count=counts.get(c.id, 0),
            )
        )
    return CaseList(items=items, total=total, limit=limit, offset=offset)


def case_detail(db: Session, case: Case) -> CaseDetail:
    base = to_response(db, case, replay=False)
    return CaseDetail(
        **base.model_dump(),
        reviews=[review_out(r, case.case_ref) for r in case.reviews],
    )