from fastapi import APIRouter

from ..config import settings
from ..schemas.meta import MetaResponse, ReasonCodesResponse
from ..schemas.result import Versions
from ..schemas.review import ALLOWED_DECISIONS
from ..services import uploads
from ..services.reason_codes import load_reason_codes

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/meta", response_model=MetaResponse, summary="Shared product metadata and policy text")
def meta():
    return MetaResponse(
        product_name=settings.product_name,
        schema_version=settings.schema_version,
        engine_mode=settings.engine_mode,
        live_inference=False,  # becomes true only after the real model is integrated
        versions=Versions(
            classifier=settings.classifier_version,
            quality_gate=settings.quality_gate_version,
            preprocess_spec=settings.preprocess_spec_version,
        ),
        referable_threshold=settings.referable_threshold,
        confidence_policy=settings.confidence_policy,
        limitations_text=settings.limitations_text,
        clinician_statement=settings.clinician_statement,
        max_upload_mb=settings.max_upload_mb,
        accepted_content_types=[ct for _, ct in uploads.SIGNATURES],
        review_decisions=list(ALLOWED_DECISIONS),
    )


@router.get("/reason-codes", response_model=ReasonCodesResponse, summary="Reason codes (placeholder list)")
def reason_codes():
    return load_reason_codes()