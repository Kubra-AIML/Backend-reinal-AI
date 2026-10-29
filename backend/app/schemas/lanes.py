from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LaneDef(BaseModel):
    id: str
    label: Optional[str] = None
    priority: int = Field(description="Lower number = earlier in the queue. Defined by the policy file.")


class RuleWhen(BaseModel):
    """Conditions on existing result fields. All listed conditions must match."""

    model_config = ConfigDict(extra="forbid")

    quality_verdict: Optional[Literal["usable", "unusable", "not_fundus"]] = None
    grade: Optional[int] = Field(default=None, ge=0, le=4)
    referable: Optional[bool] = None
    review_flag: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one(self):
        if all(v is None for v in (self.quality_verdict, self.grade, self.referable, self.review_flag)):
            raise ValueError("a rule must have at least one condition")
        return self


class LaneRule(BaseModel):
    lane: str
    when: RuleWhen


class LanePolicy(BaseModel):
    policy_version: str
    lanes: list[LaneDef] = Field(min_length=1)
    rules: list[LaneRule] = Field(default_factory=list)
    default_lane: str

    @model_validator(mode="after")
    def check_references(self):
        ids = [lane.id for lane in self.lanes]
        if len(ids) != len(set(ids)):
            raise ValueError("lane ids must be unique")
        if self.default_lane not in ids:
            raise ValueError("default_lane must be one of the lane ids")
        for rule in self.rules:
            if rule.lane not in ids:
                raise ValueError(f"rule refers to unknown lane '{rule.lane}'")
        return self