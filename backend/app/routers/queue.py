from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.errors import ErrorResponse
from ..schemas.lanes import LanePolicy
from ..schemas.queue import QueueList
from ..services import lanes, queue

router = APIRouter(prefix="/api", tags=["queue"])

POLICY_ERRORS = {
    404: {"model": ErrorResponse, "description": "Lane policy not provided yet"},
    500: {"model": ErrorResponse, "description": "Lane policy file invalid"},
}


@router.get(
    "/lanes",
    response_model=LanePolicy,
    summary="Lane policy (read-only, supplied by Teammate 2)",
    responses=POLICY_ERRORS,
)
def get_lanes():
    return lanes.load_policy()


@router.get(
    "/queue",
    response_model=QueueList,
    summary="Case queue, filterable and sortable by lane",
    description=(
        "Lane values come only from the agreed policy file. The backend does not define clinical urgency. "
        "sort=lane orders by lane priority, then newest first within a lane."
    ),
    responses={**POLICY_ERRORS, 422: {"model": ErrorResponse, "description": "Unknown lane or bad parameter"}},
)
def get_queue(
    lane: Optional[str] = Query(None, description="Only cases in this lane id"),
    sort: Literal["lane", "newest", "oldest"] = Query("lane"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    engine: Optional[Literal["stub", "cache", "matlab"]] = Query(None),
    db: Session = Depends(get_db),
):
    return queue.build_queue(db, lane=lane, sort=sort, limit=limit, offset=offset, engine=engine)