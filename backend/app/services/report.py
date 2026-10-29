from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Case
from ..schemas.report import ReportData, ReportHeatmap
from . import case_queries

REPORT_SCHEMA_VERSION = "1.0.0"
CLINICIAN_DECISION_FIELDS = ["Clinician decision", "Clinician name", "Signature", "Date"]


def build_report(db: Session, case: Case) -> ReportData:
    detail = case_queries.case_detail(db, case)
    artifacts = detail.result.artifacts
    return ReportData(
        report_schema_version=REPORT_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc),
        case_id=detail.id,
        case_ref=detail.case_ref,
        created_at=detail.created_at,
        image_sha256=detail.image_sha256,
        result=detail.result,
        reviews=detail.reviews,
        input_image_available=bool(artifacts.input_image),
        heatmap=ReportHeatmap(available=bool(artifacts.heatmap), filename=artifacts.heatmap),
        referable_threshold=settings.referable_threshold,
        confidence_policy=settings.confidence_policy,
        benchmark_caveat=settings.benchmark_caveat,
        limitations_text=settings.limitations_text,
        clinician_statement=settings.clinician_statement,
        clinician_decision_fields=CLINICIAN_DECISION_FIELDS,
    )