from fastapi import APIRouter, Depends
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db

router = APIRouter(prefix="/api", tags=["system"])

REQUIRED_TABLES = {"cases", "reviews", "audit_events", "model_versions"}


def _database_status(db: Session) -> str:
    try:
        names = set(inspect(db.get_bind()).get_table_names())
    except Exception:
        return "error"
    return "ok" if REQUIRED_TABLES <= names else "not_migrated"


@router.get("/health")
def health(db: Session = Depends(get_db)):
    return {
        "api": "ok",
        "database": _database_status(db),
        "engine": {"mode": settings.engine_mode, "live_inference": False},
    }