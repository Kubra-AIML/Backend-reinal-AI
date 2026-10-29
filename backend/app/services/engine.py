from ..config import settings
from ..errors import ApiError
from ..schemas.result import AnalysisResult
from . import engine_stub, replay


def analyse(sha256_hex: str, case_ref: str) -> AnalysisResult:
    """Chooses the engine from configuration. Every result states which engine produced it."""
    mode = settings.engine_mode
    if mode == "matlab":
        raise ApiError(501, "engine_not_available", "The MATLAB engine is not connected to this backend yet")
    if mode not in ("stub", "cache"):
        raise ApiError(500, "invalid_engine_mode", f"Unknown ENGINE_MODE '{mode}'")
    if mode == "cache":
        hit = replay.lookup(sha256_hex, case_ref)
        if hit is not None:
            return hit
    return engine_stub.analyse(sha256_hex, case_ref)  # in cache mode, a miss is a labelled stub result