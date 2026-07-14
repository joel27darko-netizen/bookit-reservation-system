from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_roles
from app.models.user import User, RoleEnum
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def reports_page(
    request: Request,
    user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.staff)),
):
    return templates.TemplateResponse("reports.html", {"request": request, "user": user})


def _parse_dates(date_from: Optional[str], date_to: Optional[str]):
    df = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
    dt = datetime.strptime(date_to, "%Y-%m-%d") if date_to else None
    return df, dt


@router.get("/{report_type}/csv")
def export_csv(
    report_type: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.staff)),
):
    df, dt = _parse_dates(date_from, date_to)
    service = ReportService(db)
    buffer = service.to_csv(report_type, df, dt)
    filename = f"{report_type}_report.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{report_type}/pdf")
def export_pdf(
    report_type: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.staff)),
):
    df, dt = _parse_dates(date_from, date_to)
    service = ReportService(db)
    buffer = service.to_pdf(report_type, df, dt)
    filename = f"{report_type}_report.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
