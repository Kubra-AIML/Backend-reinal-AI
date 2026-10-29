"""Creates a SYNTHETIC replay entry for an image, so replay mode can be demonstrated.

The entry is copied from a stub fixture and clearly marked synthetic. It is NOT a real model output.
Real precomputed outputs must come from the project lead.

Run from the backend folder:
  python scripts/make_synthetic_replay.py path/to/image.jpg [fixture_name]
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.services.fixtures import FIXTURE_NAMES, load_fixture  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python scripts/make_synthetic_replay.py path/to/image.jpg [fixture_name]")
    image = Path(sys.argv[1])
    fixture = sys.argv[2] if len(sys.argv) > 2 else "grade2"
    if fixture not in FIXTURE_NAMES:
        sys.exit(f"Unknown fixture '{fixture}'. Choose from: {', '.join(FIXTURE_NAMES)}")

    sha = hashlib.sha256(image.read_bytes()).hexdigest()
    data = load_fixture(fixture).model_dump(mode="json")
    data["engine"] = "cache"
    data["case_ref"] = None
    data["notice"] = (
        f"SYNTHETIC REPLAY ENTRY: copied from stub fixture '{fixture}'. "
        "This is not a real model output and not a real prediction."
    )
    out = settings.replay_dir / f"{sha}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()