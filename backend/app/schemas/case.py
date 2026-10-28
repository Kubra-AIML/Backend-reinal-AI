from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .result import AnalysisResult
from .review import ReviewOut


class DuplicateWarning(BaseModel):
    is_duplicate: bool
    existing_case_refs: list[str]
    message: Optional[str] = None


class CaseResponse(BaseModel):
    id: str
    case_ref: str
    created_at: datetime
    image_sha256: str
    content_type: str
    size_bytes: int
    engine: str
    idempotent_replay: bool = False
    duplicate_warning: DuplicateWarning
    result: AnalysisResult


class CaseDetail(CaseResponse):
    """The original result is never changed; reviews are listed separately, oldest first."""

    reviews: list[ReviewOut] = []


class CaseSummary(BaseModel):
    id: str
    case_ref: str
    created_at: datetime
    engine: str
    quality_verdict: str
    grade: Optional[int] = None
    referable: Optional[bool] = None
    review_flags: list[str] = []
    review_count: int = 0


class CaseList(BaseModel):
    items: list[CaseSummary]
    total: int
    limit: int
    offset: int