from fastapi import APIRouter
from ..config import settings

router = APIRouter(prefix="/api", tags=["system"])

@router.get("/health")
def health():
    return {
        "api": "ok",
        "database": "not_configured",
        "engine": {"mode": settings.engine_mode, "live_inference": False},
    }