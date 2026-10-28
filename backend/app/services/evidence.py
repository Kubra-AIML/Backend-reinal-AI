import json
from typing import Any

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


def list_evidence() -> list[dict]:
    return [{"name": n, "available": evidence_path(n).is_file()} for n in EVIDENCE_NAMES]


def load_evidence(name: str) -> Any:
    if name not in EVIDENCE_NAMES:
        raise ApiError(404, "unknown_evidence", f"Unknown evidence file: {name}")
    path = evidence_path(name)
    if not path.is_file():
        raise ApiError(404, "evidence_not_ready", f"Evidence file '{name}' has not been provided yet")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ApiError(500, "evidence_invalid", f"Evidence file '{name}' is not valid JSON")