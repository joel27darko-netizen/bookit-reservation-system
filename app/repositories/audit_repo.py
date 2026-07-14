from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, log: AuditLog) -> AuditLog:
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_recent(self, limit: int = 200) -> List[AuditLog]:
        return self.db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

    def list_paginated(self, page: int = 1, page_size: int = 25):
        q = self.db.query(AuditLog).order_by(AuditLog.created_at.desc())
        total = q.count()
        page = max(1, page)
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total
