from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .result import AnalysisResult


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