from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.resource import ResourceTypeEnum


class ResourceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: ResourceTypeEnum
    location: Optional[str] = None
    capacity: int = Field(1, ge=1)
    description: Optional[str] = None
    price_per_hour: float = Field(0.0, ge=0)
    open_time: str = "08:00"
    close_time: str = "20:00"

    @field_validator("open_time", "close_time")
    @classmethod
    def validate_time_format(cls, v):
        try:
            hh, mm = v.split(":")
            assert 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59
        except Exception:
            raise ValueError("Time must be in HH:MM 24-hour format")
        return v


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[ResourceTypeEnum] = None
    location: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    price_per_hour: Optional[float] = Field(None, ge=0)
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    is_active: Optional[bool] = None


class ResourceOut(ResourceBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
