import json
from typing import Optional
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories.audit_repo import AuditRepository


class AuditService:
    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log(self, actor_id: Optional[int], action: str, entity_type: str,
             entity_id: Optional[str] = None, details: Optional[dict] = None) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=json.dumps(details) if details else None,
        )
        return self.repo.add(entry)
