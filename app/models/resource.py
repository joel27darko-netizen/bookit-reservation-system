import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, Float, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ResourceTypeEnum(str, enum.Enum):
    room = "room"
    table = "table"
    equipment = "equipment"
    service = "service"


class Resource(Base):
    """
    A bookable item: a hotel room, a coworking desk/table, clinic equipment,
    a meeting room, or a service slot (e.g. a doctor's consultation).
    """
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    type = Column(Enum(ResourceTypeEnum), nullable=False, default=ResourceTypeEnum.room)
    location = Column(String(200), nullable=True)
    capacity = Column(Integer, default=1, nullable=False)
    description = Column(Text, nullable=True)

    # Pricing used for revenue reporting
    price_per_hour = Column(Float, default=0.0, nullable=False)

    # Availability rules (simple version): operating hours per day.
    open_time = Column(String(5), default="08:00")   # "HH:MM"
    close_time = Column(String(5), default="20:00")  # "HH:MM"

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    bookings = relationship("Booking", back_populates="resource")

    def __repr__(self):
        return f"<Resource {self.name} ({self.type})>"
