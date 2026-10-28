import json

from ..config import BASE_DIR

REASON_CODES_PATH = BASE_DIR / "app" / "data" / "reason_codes.json"


def load_reason_codes() -> dict:
    return json.loads(REASON_CODES_PATH.read_text(encoding="utf-8"))