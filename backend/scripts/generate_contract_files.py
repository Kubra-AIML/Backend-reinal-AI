"""Generates the stub fixtures and the JSON Schemas from the Pydantic models.

Run from the backend folder:  python scripts/generate_contract_files.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import BASE_DIR, settings  # noqa: E402
from app.schemas.errors import ErrorResponse  # noqa: E402
from app.schemas.result import AnalysisResult  # noqa: E402

FIXTURE_DIR = BASE_DIR / "app" / "fixtures"
CONTRACT_DIR = BASE_DIR / "contracts"

NOTICE = "STUB DATA: synthetic fixture. No model was run and no image was analysed."

VERSIONS = {
    "classifier": "stub-classifier-0.0",
    "quality_gate": "stub-quality-gate-0.0",
    "preprocess_spec": "stub-preprocess-0.0",
}

# PLACEHOLDER: confirm the referable definition with the project lead.
REFERABLE_GRADES = [2, 3, 4]

SCORES = {
    0: [0.90, 0.06, 0.02, 0.01, 0.01],
    1: [0.10, 0.75, 0.10, 0.03, 0.02],
    2: [0.05, 0.10, 0.70, 0.10, 0.05],
    3: [0.02, 0.05, 0.13, 0.70, 0.10],
    4: [0.01, 0.02, 0.07, 0.15, 0.75],
}


def base(case_ref, quality, prediction, action, flags):
    return {
        "schema_version": settings.schema_version,
        "engine": "stub",
        "case_ref": case_ref,
        "versions": VERSIONS,
        "quality": quality,
        "prediction": prediction,
        "recommended_action": action,
        "review_flags": flags,
        "artifacts": {"input_image": None, "heatmap": None},
        "timing_ms": 0.0,
        "notice": NOTICE,
    }


def graded(grade):
    scores = SCORES[grade]
    p_ref = round(sum(scores[g] for g in REFERABLE_GRADES), 4)
    return base(
        case_ref=f"STUB-G{grade}",
        quality={
            "verdict": "usable",
            "reason_codes": [],
            "metrics": {"sharpness": 0.82, "illumination": 0.77},
        },
        prediction={
            "grade": grade,
            "class_scores": scores,
            "p_referable": p_ref,
            "referable": p_ref >= settings.referable_threshold,
            "confidence": max(scores),
            "calibration_status": "uncalibrated",
        },
        action="Synthetic example only. A clinician reviews the image and decides.",
        flags=[],
    )


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    fixtures = {f"grade{g}": graded(g) for g in range(5)}
    fixtures["unusable_blurry"] = base(
        case_ref="STUB-BLUR",
        quality={
            "verdict": "unusable",
            "reason_codes": ["blur_excessive"],
            "metrics": {"sharpness": 0.12, "illumination": 0.70},
        },
        prediction=None,
        action="Recapture the image: it is too blurry to analyse. No grade is given.",
        flags=["recapture_required"],
    )
    fixtures["non_fundus"] = base(
        case_ref="STUB-NONFUNDUS",
        quality={
            "verdict": "not_fundus",
            "reason_codes": ["not_fundus_image"],
            "metrics": {},
        },
        prediction=None,
        action="This does not look like a retinal fundus photograph. Recapture or send for manual review. No grade is given.",
        flags=["manual_review_required"],
    )

    for name, data in fixtures.items():
        AnalysisResult.model_validate(data)  # fail loudly if invalid
        write_json(FIXTURE_DIR / f"{name}.json", data)

    write_json(CONTRACT_DIR / "analysis_result.schema.json", AnalysisResult.model_json_schema())
    write_json(CONTRACT_DIR / "error_response.schema.json", ErrorResponse.model_json_schema())
    print(f"Wrote {len(fixtures)} fixtures and 2 JSON Schemas.")


if __name__ == "__main__":
    main()