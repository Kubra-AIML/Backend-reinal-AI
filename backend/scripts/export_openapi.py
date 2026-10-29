"""Exports the API contract to contracts/openapi.json.

Run from the backend folder:  python scripts/export_openapi.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import BASE_DIR  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    path = BASE_DIR / "contracts" / "openapi.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()