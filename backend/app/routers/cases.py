from typing import Optional

from fastapi import APIRouter, Depends, File, Header, Request, Response, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..schemas.case import CaseResponse
from ..schemas.errors import ErrorResponse
from ..services import cases as case_service
from ..services import uploads

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