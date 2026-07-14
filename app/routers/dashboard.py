from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User, RoleEnum
from app.services.dashboard_service import DashboardService
from app.services.notification_service import NotificationService
from app.repositories.audit_repo import AuditRepository

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def root(user: Optional[User] = Depends(get_current_user)):
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = DashboardService(db)
    summary = service.summary(user)
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": user, "summary": summary}
    )


@router.get("/calendar", response_class=HTMLResponse)
def calendar_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse("calendar.html", {"request": request, "user": user})


@router.get("/calendar/events")
def calendar_events(
    resource_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = DashboardService(db)
    resource_id_int = int(resource_id) if resource_id else None
    return JSONResponse(service.calendar_events(resource_id_int, user=user))


@router.get("/notifications", response_class=HTMLResponse)
def notifications_outbox(
    request: Request,
    user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.staff)),
):
    outbox = NotificationService.get_outbox()
    return templates.TemplateResponse("notifications.html", {"request": request, "user": user, "outbox": outbox})


@router.get("/audit-log", response_class=HTMLResponse)
def audit_log_page(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin)),
):
    repo = AuditRepository(db)
    page = max(1, page)
    page_size = 25
    logs, total = repo.list_paginated(page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return templates.TemplateResponse(
        "audit_log.html",
        {"request": request, "user": user, "logs": logs, "page": page, "total_pages": total_pages, "total_count": total},
    )
