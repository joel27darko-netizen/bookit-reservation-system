"""
Booking service: the "smart booking engine".

Responsibilities:
  - Real-time availability checking (prevents double bookings)
  - Enforcing resource operating hours
  - Booking creation, rescheduling, cancellation
  - Pricing calculation
  - Emitting audit log entries + simulated notifications

This is intentionally the thickest layer in the app -- routers stay thin
and repositories stay dumb; all rules live here so they're easy to test
and reason about in one place.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.booking import Booking, BookingStatusEnum
from app.models.resource import Resource
from app.models.user import User
from app.repositories.booking_repo import BookingRepository
from app.repositories.resource_repo import ResourceRepository
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


class BookingConflictError(Exception):
    """Raised when a requested slot overlaps an existing active booking."""


class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.booking_repo = BookingRepository(db)
        self.resource_repo = ResourceRepository(db)
        self.audit = AuditService(db)

    # ---------- Availability engine ----------

    def _within_operating_hours(self, resource: Resource, start: datetime, end: datetime) -> bool:
        """Check the requested window sits within the resource's daily open/close hours."""
        open_h, open_m = map(int, resource.open_time.split(":"))
        close_h, close_m = map(int, resource.close_time.split(":"))

        day_open = start.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
        day_close = start.replace(hour=close_h, minute=close_m, second=0, microsecond=0)

        # Booking must start/end on the same calendar day and within hours.
        return start.date() == end.date() and day_open <= start and end <= day_close

    def is_available(self, resource_id: int, start: datetime, end: datetime,
                      exclude_booking_id: Optional[int] = None) -> bool:
        """Public availability check used by the UI before submission."""
        resource = self.resource_repo.get_by_id(resource_id)
        if not resource or not resource.is_active:
            return False
        if not self._within_operating_hours(resource, start, end):
            return False
        overlaps = self.booking_repo.find_overlapping(resource_id, start, end, exclude_booking_id)
        return len(overlaps) == 0

    def get_availability_slots(self, resource_id: int, day: datetime, slot_minutes: int = None) -> List[dict]:
        """
        Generate the day's bookable slots with an availability flag, for
        rendering in the UI (e.g. a simple slot picker or calendar overlay).
        """
        resource = self.resource_repo.get_by_id(resource_id)
        if not resource:
            return []
        slot_minutes = slot_minutes or settings.DEFAULT_SLOT_MINUTES

        open_h, open_m = map(int, resource.open_time.split(":"))
        close_h, close_m = map(int, resource.close_time.split(":"))
        cursor = day.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
        day_close = day.replace(hour=close_h, minute=close_m, second=0, microsecond=0)

        slots = []
        while cursor + timedelta(minutes=slot_minutes) <= day_close:
            slot_end = cursor + timedelta(minutes=slot_minutes)
            available = self.is_available(resource_id, cursor, slot_end)
            slots.append({"start": cursor, "end": slot_end, "available": available})
            cursor = slot_end
        return slots

    # ---------- Pricing ----------

    @staticmethod
    def _calculate_price(resource: Resource, start: datetime, end: datetime) -> float:
        hours = (end - start).total_seconds() / 3600
        return round(hours * resource.price_per_hour, 2)

    # ---------- Core operations ----------

    def create_booking(
        self,
        resource_id: int,
        start_time: datetime,
        end_time: datetime,
        customer: User,
        party_size: int = 1,
        notes: Optional[str] = None,
        acting_user: Optional[User] = None,
    ) -> Booking:
        resource = self.resource_repo.get_by_id(resource_id)
        if not resource or not resource.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Resource not found or inactive")

        if party_size > resource.capacity:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Party size {party_size} exceeds resource capacity {resource.capacity}",
            )

        if not self._within_operating_hours(resource, start_time, end_time):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Requested time is outside operating hours ({resource.open_time}-{resource.close_time})",
            )

        if start_time < datetime.now():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot book a time in the past")

        # --- Critical section: conflict detection ---
        overlaps = self.booking_repo.find_overlapping(resource_id, start_time, end_time)
        if overlaps:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This resource is already booked for part or all of the requested time window",
            )

        booking = Booking(
            resource_id=resource_id,
            customer_id=customer.id,
            start_time=start_time,
            end_time=end_time,
            status=BookingStatusEnum.confirmed,
            party_size=party_size,
            notes=notes,
            total_price=self._calculate_price(resource, start_time, end_time),
        )
        booking = self.booking_repo.create(booking)

        self.audit.log(
            actor_id=(acting_user or customer).id,
            action="booking.create",
            entity_type="Booking",
            entity_id=booking.id,
            details={"resource_id": resource_id, "start": str(start_time), "end": str(end_time)},
        )
        NotificationService.booking_confirmation(booking, resource, customer.email)
        return booking

    def reschedule_booking(
        self, booking_id: int, new_start: datetime, new_end: datetime, acting_user: User
    ) -> Booking:
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
        if booking.status not in (BookingStatusEnum.confirmed,):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only confirmed bookings can be rescheduled")

        resource = self.resource_repo.get_by_id(booking.resource_id)
        if not self._within_operating_hours(resource, new_start, new_end):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Requested time is outside operating hours")

        overlaps = self.booking_repo.find_overlapping(
            booking.resource_id, new_start, new_end, exclude_booking_id=booking.id
        )
        if overlaps:
            raise HTTPException(status.HTTP_409_CONFLICT, "New time conflicts with another booking")

        old_start, old_end = booking.start_time, booking.end_time
        booking.start_time = new_start
        booking.end_time = new_end
        booking.total_price = self._calculate_price(resource, new_start, new_end)
        booking = self.booking_repo.update(booking)

        self.audit.log(
            actor_id=acting_user.id,
            action="booking.reschedule",
            entity_type="Booking",
            entity_id=booking.id,
            details={"old_start": str(old_start), "old_end": str(old_end),
                     "new_start": str(new_start), "new_end": str(new_end)},
        )
        NotificationService.booking_rescheduled(booking, resource, booking.customer.email, old_start, old_end)
        return booking

    def cancel_booking(self, booking_id: int, acting_user: User) -> Booking:
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
        if booking.status == BookingStatusEnum.cancelled:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Booking already cancelled")

        # Enforce cancellation window unless staff/admin.
        if acting_user.role.value == "customer":
            hours_until_start = (booking.start_time - datetime.now()).total_seconds() / 3600
            if hours_until_start < settings.CANCELLATION_WINDOW_HOURS:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Cancellations require at least {settings.CANCELLATION_WINDOW_HOURS}h notice",
                )

        booking.status = BookingStatusEnum.cancelled
        booking = self.booking_repo.update(booking)

        resource = self.resource_repo.get_by_id(booking.resource_id)
        self.audit.log(
            actor_id=acting_user.id,
            action="booking.cancel",
            entity_type="Booking",
            entity_id=booking.id,
        )
        NotificationService.booking_cancellation(booking, resource, booking.customer.email)
        return booking

    def check_in(self, reference: str, acting_user: User) -> Booking:
        """Simulated QR scan check-in."""
        booking = self.booking_repo.get_by_reference(reference)
        if not booking:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No booking found for this QR code")
        if booking.status == BookingStatusEnum.cancelled:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This booking was cancelled")
        if booking.status == BookingStatusEnum.checked_in:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already checked in")

        booking.status = BookingStatusEnum.checked_in
        booking.checked_in_at = datetime.now()
        booking = self.booking_repo.update(booking)

        self.audit.log(
            actor_id=acting_user.id,
            action="booking.check_in",
            entity_type="Booking",
            entity_id=booking.id,
        )
        return booking

    def list_bookings(self, **filters) -> List[Booking]:
        return self.booking_repo.list_by_filters(**filters)

    def list_bookings_paginated(self, page: int = 1, page_size: int = 15, **filters):
        return self.booking_repo.list_by_filters_paginated(page=page, page_size=page_size, **filters)
