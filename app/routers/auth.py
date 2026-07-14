from fastapi import APIRouter, Depends, Request, Response, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService
from app.core.deps import get_current_user_optional
from app.core.rate_limit import check_rate_limit, record_failure, record_success

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


def _client_ip(request: Request) -> str:
    # Respect a reverse proxy's forwarded header if present, else fall back
    # to the direct connecting client.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _set_auth_cookie(response, token: str) -> None:
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=settings.ENV != "development",
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user=Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login_submit(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    ip = _client_ip(request)
    try:
        check_rate_limit(ip, email)
    except Exception as e:
        detail = getattr(e, "detail", "Too many attempts. Please wait and try again.")
        return templates.TemplateResponse("login.html", {"request": request, "error": detail}, status_code=429)

    service = AuthService(db)
    try:
        user = service.authenticate(email, password)
    except Exception as e:
        record_failure(ip, email)
        detail = getattr(e, "detail", "Login failed")
        return templates.TemplateResponse("login.html", {"request": request, "error": detail}, status_code=400)

    record_success(ip, email)
    token = service.issue_token(user)
    redirect = RedirectResponse("/dashboard", status_code=302)
    _set_auth_cookie(redirect, token)
    return redirect


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user=Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register")
def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    ip = _client_ip(request)
    try:
        check_rate_limit(ip, email)
    except Exception as e:
        detail = getattr(e, "detail", "Too many attempts. Please wait and try again.")
        return templates.TemplateResponse("register.html", {"request": request, "error": detail}, status_code=429)

    service = AuthService(db)
    try:
        data = UserCreate(full_name=full_name, email=email, password=password)
    except ValidationError as e:
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": e.errors()[0]["msg"]}, status_code=400
        )

    try:
        user = service.register(data)
    except Exception as e:
        record_failure(ip, email)
        detail = getattr(e, "detail", "Registration failed")
        return templates.TemplateResponse("register.html", {"request": request, "error": detail}, status_code=400)

    record_success(ip, email)
    token = service.issue_token(user)
    redirect = RedirectResponse("/dashboard", status_code=302)
    _set_auth_cookie(redirect, token)
    return redirect


@router.get("/logout")
def logout():
    redirect = RedirectResponse("/login", status_code=302)
    redirect.delete_cookie(settings.COOKIE_NAME)
    return redirect
