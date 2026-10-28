from typing import Any

from fastapi import APIRouter

from ..schemas.errors import ErrorResponse
from ..schemas.meta import EvidenceIndex
from ..services import evidence

router = APIRouter(prefix="/api", tags=["evidence"])


@router.get("/evidence", response_model=EvidenceIndex, summary="Which evidence files are available")
def evidence_index():
    return {"files": evidence.list_evidence()}


@router.get(
    "/evidence/{name}",
    summary="Serve one evidence JSON file",
    responses={404: {"model": ErrorResponse, "description": "Unknown name, or file not provided yet"}},
)
def evidence_file(name: str) -> Any:
    return evidence.load_evidence(name)