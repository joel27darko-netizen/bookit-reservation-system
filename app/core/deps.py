"""
FastAPI dependency-injection helpers:
  - get_current_user: reads JWT from the httpOnly cookie, validates it,
    loads the User from DB.
  - require_roles(...): factory that produces a dependency enforcing
    role-based access control on a route.

Using dependencies (rather than decorators) keeps routers thin and makes
the auth logic independently testable.
"""
from typing import Optional, Callable

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import decode_access_token
from app.config import settings
from app.models.user import User, RoleEnum
from app.repositories.user_repo import UserRepository


def get_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(settings.COOKIE_NAME)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Resolve the logged-in user from the JWT cookie, or raise 401."""
    token = get_token_from_cookie(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising (for public pages)."""
    token = get_token_from_cookie(request)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_repo = UserRepository(db)
    return user_repo.get_by_id(int(payload["sub"]))


def require_roles(*allowed_roles: RoleEnum) -> Callable:
    """
    Dependency factory for RBAC.
    Usage: Depends(require_roles(RoleEnum.admin, RoleEnum.staff))
    """
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in allowed_roles]}",
            )
        return current_user
    return dependency
