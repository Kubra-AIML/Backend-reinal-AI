from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ModelEntry(BaseModel):
    id: str
    classifier: str
    quality_gate: str
    preprocess_spec: str
    dataset_split: Optional[str] = None
    run_id: Optional[str] = None
    attribution_method_version: Optional[str] = None
    notes: Optional[str] = None


class Registry(BaseModel):
    registry_version: str
    active: str
    models: list[ModelEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def check_active_and_unique(self):
        ids = [m.id for m in self.models]
        if len(ids) != len(set(ids)):
            raise ValueError("model ids must be unique")
        if self.active not in ids:
            raise ValueError("'active' must match one of the model ids")
        return self


class ActiveModelResponse(BaseModel):
    registry_version: str
    model: ModelEntry