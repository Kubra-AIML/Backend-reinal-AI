from fastapi import APIRouter

from ..schemas.errors import ErrorResponse
from ..schemas.registry import ActiveModelResponse, Registry
from ..services import registry

router = APIRouter(prefix="/api", tags=["models"])

REGISTRY_ERRORS = {
    404: {"model": ErrorResponse, "description": "Registry not provided yet"},
    500: {"model": ErrorResponse, "description": "Registry file invalid"},
}


@router.get("/models", response_model=Registry, summary="Model registry (read-only)", responses=REGISTRY_ERRORS)
def list_models():
    return registry.load_registry()


@router.get(
    "/models/active",
    response_model=ActiveModelResponse,
    summary="Active model metadata (read-only)",
    responses=REGISTRY_ERRORS,
)
def active_model():
    return registry.active_model()