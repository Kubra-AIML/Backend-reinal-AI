from ..config import BASE_DIR
from ..schemas.result import AnalysisResult

FIXTURE_DIR = BASE_DIR / "app" / "fixtures"

FIXTURE_NAMES = [
    "grade0",
    "grade1",
    "grade2",
    "grade3",
    "grade4",
    "unusable_blurry",
    "non_fundus",
]


def load_fixture(name: str) -> AnalysisResult:
    if name not in FIXTURE_NAMES:
        raise KeyError(f"Unknown fixture: {name}")
    path = FIXTURE_DIR / f"{name}.json"
    return AnalysisResult.model_validate_json(path.read_text(encoding="utf-8"))