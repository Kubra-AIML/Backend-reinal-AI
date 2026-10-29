from datetime import datetime
from typing import Literal, Optional, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

Decision = Literal["agree", "override", "recapture", "refer"]  # PLACEHOLDER: confirm with project lead
ALLOWED_DECISIONS = get_args(Decision)


class ReviewCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"reviewer": "dr_example", "decision": "agree"},
                {
                    "reviewer": "dr_example",
                    "decision": "override",
                    "corrected_grade": 3,
                    "notes": "Example only. Do not enter patient-identifying details.",
                },
            ]
        }
    )

    reviewer: str = Field(min_length=1, max_length=100, description="Reviewer name or ID (self-declared, no login yet)")
    decision: Decision
    corrected_grade: Optional[int] = Field(default=None, ge=0, le=4)
    notes: Optional[str] = Field(default=None, max_length=2000, description="Do not enter patient-identifying details")

    @model_validator(mode="after")
    def check_grade_rules(self):
        if self.decision == "override" and self.corrected_grade is None:
            raise ValueError("corrected_grade is required when decision is 'override'")
        if self.decision != "override" and self.corrected_grade is not None:
            raise ValueError("corrected_grade is only allowed when decision is 'override'")
        return self


class ReviewOut(BaseModel):
    id: str
    case_id: str
    case_ref: str
    reviewer: str
    decision: str
    corrected_grade: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime