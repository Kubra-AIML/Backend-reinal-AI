from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Versions(BaseModel):
    classifier: str
    quality_gate: str
    preprocess_spec: str


class Quality(BaseModel):
    verdict: Literal["usable", "unusable", "not_fundus"]
    reason_codes: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class Prediction(BaseModel):
    grade: int = Field(ge=0, le=4)
    class_scores: list[float] = Field(min_length=5, max_length=5)
    p_referable: float = Field(ge=0.0, le=1.0)
    referable: bool
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    calibration_status: Literal["uncalibrated", "calibrated"]

    @model_validator(mode="after")
    def scores_sum_to_one(self):
        if any(s < 0 or s > 1 for s in self.class_scores):
            raise ValueError("each class score must be between 0 and 1")
        if abs(sum(self.class_scores) - 1.0) > 0.01:
            raise ValueError("class_scores must sum to 1 (within 0.01)")
        return self


class Artifacts(BaseModel):
    input_image: Optional[str] = None
    heatmap: Optional[str] = None


class AnalysisResult(BaseModel):
    schema_version: str
    engine: Literal["stub", "cache", "matlab"]
    case_ref: Optional[str] = None
    versions: Versions
    quality: Quality
    prediction: Optional[Prediction] = None
    recommended_action: str
    review_flags: list[str] = Field(default_factory=list)
    artifacts: Artifacts = Field(default_factory=Artifacts)
    timing_ms: Optional[float] = Field(default=None, ge=0)
    notice: Optional[str] = None

    @model_validator(mode="after")
    def check_consistency(self):
        if self.quality.verdict == "usable":
            if self.prediction is None:
                raise ValueError("usable quality verdict requires a prediction")
        elif self.prediction is not None:
            raise ValueError("no prediction allowed when quality verdict is not usable")
        if self.engine in ("stub", "cache") and not self.notice:
            raise ValueError("stub/cache results must carry a notice saying they are not live inference")
        return self