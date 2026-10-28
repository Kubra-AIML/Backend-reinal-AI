import uuid
from datetime import timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models import Case
from ..schemas.case import CaseResponse, DuplicateWarning
from ..schemas.result import AnalysisResult
from . import engine_stub
from .audit import record_event
from .model_versions import get_or_create_model_version


def new_case_ref() -> str:
    return "RG-" + uuid.uuid4().hex[:8].upper()


def get_by_idempotency_key(db: Session, key: str) -> Optional[Case]:
    return db.scalars(select(Case).where(Case.idempotency_key == key)).first()


def find_duplicates(db: Session, sha256: str, exclude_id: Optional[str] = None) -> list[str]:
    stmt = select(Case.case_ref).where(Case.image_sha256 == sha256).order_by(Case.created_at.asc())
    if exclude_id is not None:
        stmt = stmt.where(Case.id != exclude_id)
    return list(db.scalars(stmt).all())


def _replay_or_conflict(existing: Case, sha256: str) -> Case:
    if existing.image_sha256 != sha256:
        raise ApiError(
            409,
            "idempotency_key_reused",
            "This Idempotency-Key was already used with a different file",
        )
    return existing


def create_case(
    db: Session,
    *,
    data: bytes,
    content_type: str,
    sha256: str,
    idempotency_key: Optional[str],
    request_id: Optional[str],
) -> tuple[Case, bool]:
    """Returns (case, created). created is False when an earlier case is returned for a repeated key."""
    if idempotency_key:
        existing = get_by_idempotency_key(db, idempotency_key)
        if existing is not None:
            return _replay_or_conflict(existing, sha256), False

    case_ref = new_case_ref()
    result = engine_stub.analyse(sha256, case_ref)

    try:
        mv = get_or_create_model_version(db, result.versions, result.engine)
        case = Case(
            case_ref=case_ref,
            image_sha256=sha256,
            content_type=content_type,
            size_bytes=len(data),
            idempotency_key=idempotency_key,
            engine=result.engine,
            model_version_id=mv.id,
            result_json=result.model_dump_json(),
        )
        db.add(case)
        db.flush()

        duplicates = find_duplicates(db, sha256, exclude_id=case.id)
        record_event(
            db,
            "upload_received",
            case_id=case.id,
            request_id=request_id,
            details={"sha256": sha256, "size_bytes": len(data), "content_type": content_type},
        )
        if duplicates:
            record_event(
                db,
                "duplicate_upload_detected",
                case_id=case.id,
                request_id=request_id,
                details={"existing_case_refs": duplicates},
            )
        record_event(
            db,
            "analysis_requested",
            case_id=case.id,
            request_id=request_id,
            details={"engine": result.engine},
        )
        db.commit()
    except IntegrityError:
        # Two identical requests raced: the database's unique key let only one win.
        db.rollback()
        if idempotency_key:
            existing = get_by_idempotency_key(db, idempotency_key)
            if existing is not None:
                return _replay_or_conflict(existing, sha256), False
        raise
    return case, True


def to_response(db: Session, case: Case, replay: bool) -> CaseResponse:
    refs = find_duplicates(db, case.image_sha256, exclude_id=case.id)
    created_at = case.created_at
    if created_at.tzinfo is None:  # SQLite returns naive datetimes; we store UTC
        created_at = created_at.replace(tzinfo=timezone.utc)
    return CaseResponse(
        id=case.id,
        case_ref=case.case_ref,
        created_at=created_at,
        image_sha256=case.image_sha256,
        content_type=case.content_type,
        size_bytes=case.size_bytes,
        engine=case.engine,
        idempotent_replay=replay,
        duplicate_warning=DuplicateWarning(
            is_duplicate=bool(refs),
            existing_case_refs=refs,
            message="An image with the same SHA-256 was uploaded before." if refs else None,
        ),
        result=AnalysisResult.model_validate_json(case.result_json),
    )