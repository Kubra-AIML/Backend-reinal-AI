import json
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from ..config import settings
from ..errors import ApiError

# Fixed allow-list: the name in the URL can never be used to reach other files.
EVIDENCE_NAMES = (
    "evaluation_summary",
    "operating_points",
    "robustness_checks",
    "explanation_checks",
    "simulation_presets",
)


def evidence_path(name: str):
    return settings.evidence_dir / f"{name}.json"


def schema_path(name: str):
    return settings.evidence_dir / "schemas" / f"{name}.schema.json"


def list_evidence() -> list[dict]:
    return [{"name": n, "available": evidence_path(n).is_file()} for n in EVIDENCE_NAMES]


def load_evidence(name: str) -> Any:
    if name not in EVIDENCE_NAMES:
        raise ApiError(404, "unknown_evidence", f"Unknown evidence file: {name}")
    path = evidence_path(name)
    if not path.is_file():
        raise ApiError(404, "evidence_not_ready", f"Evidence file '{name}' has not been provided yet")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ApiError(500, "evidence_invalid", f"Evidence file '{name}' is not valid JSON")

    # Built-in check: every evidence file must be a JSON object.
    if not isinstance(data, dict):
        raise ApiError(500, "evidence_invalid", f"Evidence file '{name}' must be a JSON object")

    # Optional stricter check, active only once a schema file is supplied for this evidence file.
    sp = schema_path(name)
    if sp.is_file():
        try:
            schema = json.loads(sp.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (OSError, ValueError, SchemaError):
            raise ApiError(500, "evidence_schema_invalid", f"The schema for '{name}' is not valid")
        errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: [str(p) for p in e.path])
        if errors:
            raise ApiError(
                500,
                "evidence_invalid",
                f"Evidence file '{name}' does not match its schema",
                details=[{"path": "/".join(str(p) for p in e.path), "message": e.message} for e in errors[:10]],
            )
    return data