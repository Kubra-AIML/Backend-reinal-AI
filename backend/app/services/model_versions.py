from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ModelVersion
from ..schemas.result import Versions


def get_or_create_model_version(db: Session, versions: Versions, engine: str) -> ModelVersion:
    stmt = select(ModelVersion).where(
        ModelVersion.classifier == versions.classifier,
        ModelVersion.quality_gate == versions.quality_gate,
        ModelVersion.preprocess_spec == versions.preprocess_spec,
        ModelVersion.engine == engine,
    )
    existing = db.scalars(stmt).first()
    if existing:
        return existing
    mv = ModelVersion(
        classifier=versions.classifier,
        quality_gate=versions.quality_gate,
        preprocess_spec=versions.preprocess_spec,
        engine=engine,
    )
    db.add(mv)
    db.flush()
    return mv