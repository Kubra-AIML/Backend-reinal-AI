from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")
    product_name: str = "RetinaGuide XAI"
    engine_mode: str = "stub"  # stub | cache | matlab
    database_url: str = "sqlite:///./retinaguide.db"
    max_upload_mb: int = 10
    referable_threshold: float = 0.5
    schema_version: str = "1.0.0"

    # Version placeholders until the project lead's model registry is available (M7).
    classifier_version: str = "stub-classifier-0.0"
    quality_gate_version: str = "stub-quality-gate-0.0"
    preprocess_spec_version: str = "stub-preprocess-0.0"

    confidence_policy: str = (
        "Class scores are uncalibrated model outputs, not calibrated probabilities. "
        "They must not be read as the chance that a diagnosis is correct."
    )
    clinician_statement: str = "This tool supports, and does not replace, clinician judgement. The clinician decides."
    limitations_text: str = "Research prototype. Not clinically validated. Not for autonomous diagnosis."

    # Folder where Teammate 2's evidence JSON files are placed.
    evidence_dir: Path = BASE_DIR / "evidence"


settings = Settings()