"""
Application entrypoint.

Wires together: DB table creation (dev convenience -- use Alembic
migrations in production), logging, security headers, global exception
handling, static files, and all routers.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 - ensures models are registered on Base.metadata

from app.routers import auth, resources, bookings, dashboard, reports, checkin, users, profile

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("bookit")

# ---------- App ----------
app = FastAPI(title=settings.APP_NAME)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# ---------- Security headers ----------
# Baseline hardening: clickjacking, MIME-sniffing, and referrer leakage
# protections applied to every response. CSP is intentionally left off
# here since the app relies on several CDN scripts (Bootstrap, FullCalendar,
# Chart.js) -- a real deployment should pin those in a CSP allowlist.
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if settings.ENV != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.on_event("startup")
def on_startup():
    # Dev convenience: auto-create tables. Use `alembic upgrade head` in prod.
    Base.metadata.create_all(bind=engine)

    if "CHANGE_ME" in settings.SECRET_KEY:
        logger.warning(
            "SECRET_KEY is still the default placeholder -- set a real, "
            "unique SECRET_KEY via environment variable before deploying."
        )
    logger.info(f"{settings.APP_NAME} started (env={settings.ENV})")


# ---------- Global error handling ----------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Render a friendly error page for browser navigations; return JSON for
    API-style/XHR requests (Accept: application/json or path starts with
    known JSON endpoints).
    """
    logger.warning(f"HTTPException {exc.status_code} on {request.url.path}: {exc.detail}")

    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/login", status_code=302)

    wants_json = "application/json" in request.headers.get("accept", "")
    if wants_json:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status_code": exc.status_code, "detail": exc.detail},
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.url.path}")
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status_code": 500, "detail": "An unexpected error occurred."},
        status_code=500,
    )


# ---------- Routers ----------
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(resources.router)
app.include_router(bookings.router)
app.include_router(reports.router)
app.include_router(checkin.router)
app.include_router(users.router)
app.include_router(profile.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
