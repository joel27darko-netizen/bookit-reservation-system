from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_roles
from app.models.user import User, RoleEnum
from app.repositories.user_repo import UserRepository
from app.services.audit_service import AuditService

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin)),
):
    repo = UserRepository(db)
    users = repo.list_all()
    return templates.TemplateResponse("users.html", {"request": request, "user": user, "users": users, "roles": list(RoleEnum)})


@router.post("/{user_id}/role")
def update_role(
    user_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(RoleEnum.admin)),
):
    repo = UserRepository(db)
    target = repo.get_by_id(user_id)
    if target:
        old_role = target.role.value
        target.role = RoleEnum(role)
        repo.update(target)
        AuditService(db).log(user.id, "user.role_change", "User", user_id,
                              {"old_role": old_role, "new_role": role})
    return RedirectResponse("/users", status_code=302)
