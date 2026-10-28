from pydantic import BaseModel

from .result import Versions


class MetaResponse(BaseModel):
    product_name: str
    schema_version: str
    engine_mode: str
    live_inference: bool
    versions: Versions
    referable_threshold: float
    confidence_policy: str
    limitations_text: str
    clinician_statement: str
    max_upload_mb: int
    accepted_content_types: list[str]
    review_decisions: list[str]


class ReasonCode(BaseModel):
    code: str
    applies_to: str
    label: str
    guidance: str


class ReasonCodesResponse(BaseModel):
    status: str
    note: str
    reason_codes: list[ReasonCode]


class EvidenceFileStatus(BaseModel):
    name: str
    available: bool


class EvidenceIndex(BaseModel):
    files: list[EvidenceFileStatus]