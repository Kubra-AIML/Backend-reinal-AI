from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.errors import ErrorResponse
from ..schemas.report import ReportData
from ..services import case_queries
from ..services.audit import record_event
from ..services.report import build_report
from ..services.report_pdf import render_pdf

router = APIRouter(prefix="/api", tags=["reports"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Case not found"}}


@router.get(
    "/cases/{case_ref}/report",
    response_model=ReportData,
    summary="Structured report (the PDF is rendered from this)",
    responses=NOT_FOUND,
)
def report_json(case_ref: str, db: Session = Depends(get_db)):
    case = case_queries.get_case_or_404(db, case_ref)
    return build_report(db, case)


@router.get(
    "/cases/{case_ref}/report.pdf",
    response_model=None,
    summary="PDF report rendered from the report JSON",
    responses={**NOT_FOUND, 200: {"content": {"application/pdf": {}}, "description": "PDF file"}},
)
def report_pdf(case_ref: str, request: Request, db: Session = Depends(get_db)):
    case = case_queries.get_case_or_404(db, case_ref)
    pdf = render_pdf(build_report(db, case))
    record_event(
        db,
        "report_downloaded",
        case_id=case.id,
        request_id=request.headers.get("x-request-id"),
        details={"format": "pdf"},
    )
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{case.case_ref}-report.pdf"'},
    )