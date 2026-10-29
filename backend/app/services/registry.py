from ..config import settings
from ..errors import ApiError
from ..schemas.registry import ActiveModelResponse, Registry


def load_registry() -> Registry:
    """Read-only. This service never writes to the registry or to any model file."""
    path = settings.registry_path
    if not path.is_file():
        raise ApiError(404, "registry_not_ready", "The model registry has not been provided yet")
    try:
        return Registry.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ApiError(500, "registry_invalid", "The model registry file is not valid")


def active_model() -> ActiveModelResponse:
    reg = load_registry()
    model = next(m for m in reg.models if m.id == reg.active)
    return ActiveModelResponse(registry_version=reg.registry_version, model=model)