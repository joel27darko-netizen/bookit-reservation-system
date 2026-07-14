from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, RoleEnum
from app.models.resource import ResourceTypeEnum
from app.schemas.resource import ResourceCreate, ResourceUpdate
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/resources", tags=["resources"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_resources_page(
    request: Request,
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ResourceService(db)
    type_filter = ResourceTypeEnum(type) if type else None
    resources = service.list_resources(only_active=True, type_filter=type_filter)
    return templates.TemplateResponse(
        "resources.html",
        {"request": request, "user": user, "resources": resources, "types": list(ResourceTypeEnum),
         "active_type": type},
    )


@router.post("/create")
def create_resource(
    name: str = Form(...),
    type: str = Form(...),
    location: str = Form(""),
    capacity: int = Form(1),
    description: str = Form(""),
    price_per_hour: float = Form(0.0),
    open_time: str = Form("08:00"),
    close_time: str = Form("20:00"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.staff)),
):
    service = ResourceService(db)
    data = ResourceCreate(
        name=name, type=type, location=location, capacity=capacity,
        description=description, price_per_hour=price_per_hour,
        open_time=open_time, close_time=close_time,
    )
    service.create(data, user)
    return RedirectResponse("/resources", status_code=302)


@router.post("/{resource_id}/update")
def update_resource(
    resource_id: int,
    name: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    capacity: Optional[int] = Form(None),
    price_per_hour: Optional[float] = Form(None),
    open_time: Optional[str] = Form(None),
    close_time: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.staff)),
):
    service = ResourceService(db)
    data = ResourceUpdate(
        name=name, location=location, capacity=capacity, price_per_hour=price_per_hour,
        open_time=open_time, close_time=close_time,
    )
    service.update(resource_id, data, user)
    return RedirectResponse("/resources", status_code=302)


@router.post("/{resource_id}/deactivate")
def deactivate_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.staff)),
):
    service = ResourceService(db)
    service.deactivate(resource_id, user)
    return RedirectResponse("/resources", status_code=302)


@router.get("/{resource_id}/availability")
def resource_availability(
    resource_id: int,
    day: str,  # YYYY-MM-DD
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """JSON endpoint used by the front-end slot picker for real-time availability."""
    from datetime import datetime
    from app.services.booking_service import BookingService

    service = BookingService(db)
    day_dt = datetime.strptime(day, "%Y-%m-%d")
    slots = service.get_availability_slots(resource_id, day_dt)
    return JSONResponse([
        {"start": s["start"].isoformat(), "end": s["end"].isoformat(), "available": s["available"]}
        for s in slots
    ])
