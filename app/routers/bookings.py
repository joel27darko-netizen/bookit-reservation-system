from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, RoleEnum
from app.models.booking import BookingStatusEnum
from app.repositories.user_repo import UserRepository
from app.services.booking_service import BookingService
from app.services.resource_service import ResourceService
from app.services.qr_service import QRService

router = APIRouter(prefix="/bookings", tags=["bookings"])
templates = Jinja2Templates(directory="app/templates")


PAGE_SIZE = 12


@router.get("", response_class=HTMLResponse)
def list_bookings_page(
    request: Request,
    resource_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BookingService(db)
    # Query params from a <select> arrive as "" when "All ..." is chosen --
    # treat blank strings the same as "not provided" instead of letting
    # FastAPI's int coercion 422 on them.
    resource_id_int = int(resource_id) if resource_id else None
    status_enum = BookingStatusEnum(status) if status else None
    df = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
    dt = datetime.strptime(date_to, "%Y-%m-%d") if date_to else None

    # Customers only ever see their own bookings; staff/admin can see all,
    # filter by any customer via search, or filter by resource/status/date.
    filters = dict(resource_id=resource_id_int, status=status_enum, date_from=df, date_to=dt)
    if user.role == RoleEnum.customer:
        filters["customer_id"] = user.id
    elif q:
        filters["customer_search"] = q

    page = max(1, page)
    bookings, total = service.list_bookings_paginated(page=page, page_size=PAGE_SIZE, **filters)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    resources = ResourceService(db).list_resources(only_active=False)

    return templates.TemplateResponse(
        "bookings.html",
        {
            "request": request, "user": user, "bookings": bookings, "resources": resources,
            "statuses": list(BookingStatusEnum),
            "filters": {
                "resource_id": resource_id_int, "status": status, "date_from": date_from,
                "date_to": date_to, "q": q,
            },
            "page": page, "total_pages": total_pages, "total_count": total,
        },
    )


@router.post("/create")
def create_booking(
    resource_id: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    party_size: int = Form(1),
    notes: str = Form(""),
    customer_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BookingService(db)
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)

    # Staff/admin may book on behalf of a customer; otherwise book for self.
    customer = user
    if customer_id and user.role in (RoleEnum.admin, RoleEnum.staff):
        customer = UserRepository(db).get_by_id(customer_id) or user

    service.create_booking(
        resource_id=resource_id, start_time=start_dt, end_time=end_dt,
        customer=customer, party_size=party_size, notes=notes, acting_user=user,
    )
    return RedirectResponse("/bookings", status_code=302)


@router.post("/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BookingService(db)
    service.cancel_booking(booking_id, user)
    return RedirectResponse("/bookings", status_code=302)


@router.post("/{booking_id}/reschedule")
def reschedule_booking(
    booking_id: int,
    start_time: str = Form(...),
    end_time: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BookingService(db)
    service.reschedule_booking(
        booking_id, datetime.fromisoformat(start_time), datetime.fromisoformat(end_time), user
    )
    return RedirectResponse("/bookings", status_code=302)


@router.get("/{booking_id}/qr", response_class=HTMLResponse)
def booking_qr(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BookingService(db)
    booking = service.booking_repo.get_by_id(booking_id)
    qr_data_uri = QRService.generate_qr_base64(booking.reference)
    return templates.TemplateResponse(
        "qr_modal.html", {"request": request, "booking": booking, "qr_data_uri": qr_data_uri}
    )
