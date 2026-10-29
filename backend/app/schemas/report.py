from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .result import AnalysisResult
from .review import ReviewOut


class ReportHeatmap(BaseModel):
    available: bool
    filename: Optional[str] = None
    label: str = (
        "Model attribution: shows image regions that influenced the model output. "
        "It is not a diagnosis and not a lesion map."
    )


class ReportData(BaseModel):
    """The one structured report. The PDF is rendered from exactly this object."""

    report_schema_version: str
    generated_at: datetime
    case_id: str
    case_ref: str
    created_at: datetime
    image_sha256: str
    result: AnalysisResult
    reviews: list[ReviewOut]
    input_image_available: bool
    heatmap: ReportHeatmap
    referable_threshold: float
    confidence_policy: str
    benchmark_caveat: str
    limitations_text: str
    clinician_statement: str
    clinician_decision_fields: list[str]