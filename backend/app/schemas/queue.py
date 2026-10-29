from typing import Optional

from pydantic import BaseModel

from .case import CaseSummary


class QueueItem(CaseSummary):
    lane: str
    lane_label: Optional[str] = None
    lane_priority: int


class QueueList(BaseModel):
    policy_version: str
    items: list[QueueItem]
    total: int
    limit: int
    offset: int
    lane: Optional[str] = None
    sort: str