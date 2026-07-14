from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.booking import BookingStatusEnum


class BookingCreate(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime
    party_size: int = Field(1, ge=1)
    notes: Optional[str] = None
    # Admin/staff can create bookings on behalf of a customer.
    customer_id: Optional[int] = None

    @model_validator(mode="after")
    def check_time_order(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class BookingReschedule(BaseModel):
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def check_time_order(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class BookingOut(BaseModel):
    id: int
    reference: str
    resource_id: int
    customer_id: int
    start_time: datetime
    end_time: datetime
    status: BookingStatusEnum
    party_size: int
    notes: Optional[str] = None
    total_price: float
    checked_in_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AvailabilityQuery(BaseModel):
    resource_id: int
    start_time: datetime
    end_time: datetime
