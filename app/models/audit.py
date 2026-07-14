from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


class AuditLog(Base):
    """
    Immutable trail of important actions (create/cancel/reschedule bookings,
    login, role changes, resource edits, etc.) for accountability and
    troubleshooting.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)       # e.g. "booking.create"
    entity_type = Column(String(50), nullable=False)   # e.g. "Booking"
    entity_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)               # free-form JSON/text
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    actor = relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} by={self.actor_id} entity={self.entity_type}:{self.entity_id}>"
