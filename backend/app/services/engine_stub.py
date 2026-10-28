from ..schemas.result import AnalysisResult
from .fixtures import FIXTURE_NAMES, load_fixture


def pick_fixture_name(sha256_hex: str) -> str:
    """Deterministic: the same file always maps to the same synthetic example."""
    return FIXTURE_NAMES[int(sha256_hex, 16) % len(FIXTURE_NAMES)]


def analyse(sha256_hex: str, case_ref: str) -> AnalysisResult:
    """STUB ENGINE. Returns a synthetic fixture. The image is NOT inspected and no model is run."""
    name = pick_fixture_name(sha256_hex)
    data = load_fixture(name).model_dump(mode="json")
    data["case_ref"] = case_ref
    data["notice"] = (
        f"{data['notice']} Example '{name}' was chosen from the file hash; the image was not inspected."
    )
    return AnalysisResult.model_validate(data)