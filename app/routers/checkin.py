from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_roles
from app.models.user import User, RoleEnum
from app.services.booking_service import BookingService
from app.services.qr_service import QRService

router = APIRouter(prefix="/checkin", tags=["checkin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def checkin_page(
    request: Request,
    user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.staff)),
):
    return templates.TemplateResponse("checkin.html", {"request": request, "user": user, "result": None})


@router.post("/scan", response_class=HTMLResponse)
def simulate_scan(
    request: Request,
    payload: str = Form(...),  # simulated QR payload, e.g. "BOOKIT:<uuid>"
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.staff)),
):
    reference = QRService.decode_payload(payload)
    service = BookingService(db)
    result = {"success": False, "message": None, "booking": None}
    try:
        booking = service.check_in(reference, user)
        result = {"success": True, "message": "Checked in successfully!", "booking": booking}
    except Exception as e:
        result = {"success": False, "message": getattr(e, "detail", str(e)), "booking": None}

    return templates.TemplateResponse("checkin.html", {"request": request, "user": user, "result": result})
