from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.user import User, RoleEnum


class UserRepository:
    """Encapsulates all raw DB queries for User. No business logic here."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def list_all(self, role: Optional[RoleEnum] = None) -> List[User]:
        q = self.db.query(User)
        if role:
            q = q.filter(User.role == role)
        return q.order_by(User.created_at.desc()).all()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user
