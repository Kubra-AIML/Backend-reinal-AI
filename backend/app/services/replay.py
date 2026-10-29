import re
from typing import Optional

from ..config import settings
from ..errors import ApiError
from ..schemas.result import AnalysisResult

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def lookup(sha256: str, case_ref: str) -> Optional[AnalysisResult]:
    """Returns a replayed result for a known image, or None when no entry exists.

    A replay entry is an AnalysisResult JSON file named <sha256>.json that declares engine "cache".
    Replayed output is never presented as live inference.
    """
    if not SHA256_PATTERN.match(sha256):
        return None
    path = settings.replay_dir / f"{sha256}.json"
    if not path.is_file():
        return None
    try:
        result = AnalysisResult.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ApiError(500, "replay_entry_invalid", "A replay entry exists for this image but is not valid")
    if result.engine != "cache":
        raise ApiError(500, "replay_entry_invalid", "Replay entries must declare engine 'cache'")

    data = result.model_dump(mode="json")
    data["case_ref"] = case_ref
    data["notice"] = (
        f"{result.notice} REPLAY: precomputed output returned for a known image "
        "(matched by SHA-256). No model was run for this request."
    )
    return AnalysisResult.model_validate(data)