from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models import Case, Review
from ..schemas.queue import QueueItem, QueueList
from ..schemas.result import AnalysisResult
from . import lanes
from .case_queries import as_utc


def build_queue(
    db: Session, *, lane: Optional[str], sort: str, limit: int, offset: int, engine: Optional[str]
) -> QueueList:
    policy = lanes.load_policy()
    by_id = {d.id: d for d in policy.lanes}
    if lane is not None and lane not in by_id:
        raise ApiError(422, "unknown_lane", f"Unknown lane '{lane}'", details={"known_lanes": list(by_id)})

    stmt = select(Case)
    if engine:
        stmt = stmt.where(Case.engine == engine)
    rows = db.scalars(stmt).all()
    counts = dict(db.execute(select(Review.case_id, func.count()).group_by(Review.case_id)).all())

    items = []
    for c in rows:
        result = AnalysisResult.model_validate_json(c.result_json)
        lane_id = lanes.lane_for(result, policy)  # computed on the fly, never stored on the case
        if lane is not None and lane_id != lane:
            continue
        pred = result.prediction
        items.append(
            QueueItem(
                id=c.id,
                case_ref=c.case_ref,
                created_at=as_utc(c.created_at),
                engine=c.engine,
                quality_verdict=result.quality.verdict,
                grade=pred.grade if pred else None,
                referable=pred.referable if pred else None,
                review_flags=result.review_flags,
                review_count=counts.get(c.id, 0),
                lane=lane_id,
                lane_label=by_id[lane_id].label,
                lane_priority=by_id[lane_id].priority,
            )
        )

    if sort == "oldest":
        items.sort(key=lambda i: i.created_at)
    else:
        items.sort(key=lambda i: i.created_at, reverse=True)  # newest first within a lane
        if sort == "lane":
            items.sort(key=lambda i: i.lane_priority)  # stable sort keeps that order inside each lane

    return QueueList(
        policy_version=policy.policy_version,
        items=items[offset : offset + limit],
        total=len(items),
        limit=limit,
        offset=offset,
        lane=lane,
        sort=sort,
    )