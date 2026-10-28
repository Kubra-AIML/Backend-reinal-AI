from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..schemas.case import CaseDetail, CaseList, CaseResponse
from ..schemas.errors import ErrorResponse
from ..schemas.review import ReviewCreate, ReviewOut
from ..services import case_queries
from ..services import cases as case_service
from ..services import uploads
from ..services.reviews import add_review

router = APIRouter(prefix="/api", tags=["cases"])


@router.post(
    "/cases",
    response_model=CaseResponse,
    status_code=201,
    summary="Upload an image and create a case",
    description=(
        "Creates a case from a JPEG or PNG upload. The file type is checked by its signature. "
        "Send an Idempotency-Key header so a retried request returns the original case (HTTP 200, "
        "Idempotent-Replay: true) instead of creating a duplicate. "
        "In stub mode the result is a synthetic example and the image is not inspected."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Empty file"},
        409: {"model": ErrorResponse, "description": "Idempotency-Key reused with a different file"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Not a JPEG or PNG"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_case(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    key = uploads.validate_idempotency_key(idempotency_key)
    data = uploads.read_limited(file.file, settings.max_upload_mb * 1024 * 1024)
    content_type = uploads.validate_image_bytes(data)
    sha256 = uploads.sha256_hex(data)

    case, created = case_service.create_case(
        db,
        data=data,
        content_type=content_type,
        sha256=sha256,
        idempotency_key=key,
        request_id=request.headers.get("x-request-id"),
    )
    if not created:
        response.status_code = 200
        response.headers["Idempotent-Replay"] = "true"
    return case_service.to_response(db, case, replay=not created)


@router.get("/cases", response_model=CaseList, summary="List cases, newest first")
def list_cases(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    engine: Optional[Literal["stub", "cache", "matlab"]] = Query(None),
    db: Session = Depends(get_db),
):
    return case_queries.list_cases(db, limit=limit, offset=offset, engine=engine)


@router.get(
    "/cases/{case_ref}",
    response_model=CaseDetail,
    summary="Case detail with reviews",
    description="Accepts the case id or the case reference (RG-XXXXXXXX). The original result is never altered by reviews.",
    responses={404: {"model": ErrorResponse, "description": "Case not found"}},
)
def get_case(case_ref: str, db: Session = Depends(get_db)):
    case = case_queries.get_case_or_404(db, case_ref)
    return case_queries.case_detail(db, case)


@router.post(
    "/cases/{case_ref}/reviews",
    response_model=ReviewOut,
    status_code=201,
    summary="Add a review (always a new record)",
    description=(
        "Appends a review. The original prediction is never overwritten. "
        "decision 'override' requires corrected_grade; other decisions must not send one. "
        "The reviewer field is self-declared (no login yet)."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Case not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_review(case_ref: str, body: ReviewCreate, request: Request, db: Session = Depends(get_db)):
    case = case_queries.get_case_or_404(db, case_ref)
    review = add_review(
        db,
        case_id=case.id,
        reviewer=body.reviewer,
        decision=body.decision,
        corrected_grade=body.corrected_grade,
        notes=body.notes,
        request_id=request.headers.get("x-request-id"),
    )
    db.commit()
    return case_queries.review_out(review, case.case_ref)