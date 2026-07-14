import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Float, Text
from sqlalchemy.orm import relationship

from app.database import Base


class BookingStatusEnum(str, enum.Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    checked_in = "checked_in"
    no_show = "no_show"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    # Public-facing unique reference, used in QR codes/check-in lookups.
    reference = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))

    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)

    status = Column(Enum(BookingStatusEnum), default=BookingStatusEnum.confirmed, nullable=False)
    party_size = Column(Integer, default=1, nullable=False)
    notes = Column(Text, nullable=True)

    total_price = Column(Float, default=0.0, nullable=False)

    checked_in_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    resource = relationship("Resource", back_populates="bookings")
    customer = relationship("User", back_populates="bookings", foreign_keys=[customer_id])

    def __repr__(self):
        return f"<Booking {self.reference} r={self.resource_id} {self.start_time}-{self.end_time}>"
