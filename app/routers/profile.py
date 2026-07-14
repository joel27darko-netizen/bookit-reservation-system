from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/profile", tags=["profile"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def profile_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "profile.html", {"request": request, "user": user, "error": None, "success": None}
    )


@router.post("/update")
def update_profile(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = AuthService(db)
    try:
        user = service.update_profile(user, full_name, email)
    except Exception as e:
        detail = getattr(e, "detail", "Couldn't update profile")
        return templates.TemplateResponse(
            "profile.html", {"request": request, "user": user, "error": detail, "success": None}, status_code=400
        )
    return templates.TemplateResponse(
        "profile.html", {"request": request, "user": user, "error": None, "success": "Profile updated."}
    )


@router.post("/password")
def update_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = AuthService(db)
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "profile.html",
            {"request": request, "user": user, "error": "New passwords don't match", "success": None},
            status_code=400,
        )
    try:
        service.change_password(user, current_password, new_password)
    except Exception as e:
        detail = getattr(e, "detail", "Couldn't change password")
        return templates.TemplateResponse(
            "profile.html", {"request": request, "user": user, "error": detail, "success": None}, status_code=400
        )
    return templates.TemplateResponse(
        "profile.html", {"request": request, "user": user, "error": None, "success": "Password changed."}
    )
