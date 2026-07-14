from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, RoleEnum
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password, create_access_token
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)
        self.audit = AuditService(db)

    def register(self, data: UserCreate, role: RoleEnum = RoleEnum.customer) -> User:
        if self.repo.get_by_email(data.email):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

        user = User(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hash_password(data.password),
            role=role,
        )
        user = self.repo.create(user)
        self.audit.log(user.id, "user.register", "User", user.id, {"email": user.email, "role": role.value})
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled")
        self.audit.log(user.id, "user.login", "User", user.id)
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(subject=str(user.id), role=user.role.value)

    def update_profile(self, user: User, full_name: str, email: str) -> User:
        if email.lower() != user.email.lower():
            existing = self.repo.get_by_email(email)
            if existing and existing.id != user.id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "That email is already in use")
        user.full_name = full_name
        user.email = email
        user = self.repo.update(user)
        self.audit.log(user.id, "user.update_profile", "User", user.id, {"email": email})
        return user

    def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
        if len(new_password) < 6:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must be at least 6 characters")
        user.hashed_password = hash_password(new_password)
        user = self.repo.update(user)
        self.audit.log(user.id, "user.change_password", "User", user.id)
        return user
