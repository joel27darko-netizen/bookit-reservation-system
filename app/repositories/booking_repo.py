from datetime import datetime
from typing import Optional, List

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatusEnum


# Statuses that actually occupy the resource (cancelled/no-show do not).
ACTIVE_STATUSES = [BookingStatusEnum.confirmed, BookingStatusEnum.checked_in, BookingStatusEnum.completed]


class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, booking_id: int) -> Optional[Booking]:
        return self.db.query(Booking).filter(Booking.id == booking_id).first()

    def get_by_reference(self, reference: str) -> Optional[Booking]:
        return self.db.query(Booking).filter(Booking.reference == reference).first()

    def find_overlapping(
        self,
        resource_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[int] = None,
    ) -> List[Booking]:
        """
        Core double-booking guard: returns any ACTIVE booking on the same
        resource whose [start,end) interval overlaps the requested window.
        Overlap condition: existing.start < new.end AND existing.end > new.start
        """
        q = self.db.query(Booking).filter(
            Booking.resource_id == resource_id,
            Booking.status.in_(ACTIVE_STATUSES),
            Booking.start_time < end_time,
            Booking.end_time > start_time,
        )
        if exclude_booking_id:
            q = q.filter(Booking.id != exclude_booking_id)
        return q.all()

    def list_by_filters(
        self,
        resource_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        status: Optional[BookingStatusEnum] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Booking]:
        q = self.db.query(Booking)
        if resource_id:
            q = q.filter(Booking.resource_id == resource_id)
        if customer_id:
            q = q.filter(Booking.customer_id == customer_id)
        if status:
            q = q.filter(Booking.status == status)
        if date_from:
            q = q.filter(Booking.end_time >= date_from)
        if date_to:
            q = q.filter(Booking.start_time <= date_to)
        return q.order_by(Booking.start_time.asc()).all()

    def list_by_filters_paginated(
        self,
        resource_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        status: Optional[BookingStatusEnum] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        customer_search: Optional[str] = None,
        page: int = 1,
        page_size: int = 15,
    ) -> tuple[List[Booking], int]:
        """Same filters as list_by_filters, but returns (page_of_items, total_count)."""
        q = self.db.query(Booking)
        if resource_id:
            q = q.filter(Booking.resource_id == resource_id)
        if customer_id:
            q = q.filter(Booking.customer_id == customer_id)
        if status:
            q = q.filter(Booking.status == status)
        if date_from:
            q = q.filter(Booking.end_time >= date_from)
        if date_to:
            q = q.filter(Booking.start_time <= date_to)
        if customer_search:
            # Free-text search across customer name/email and the booking
            # reference, so front-desk staff can find a booking either way.
            from app.models.user import User
            like = f"%{customer_search.strip()}%"
            q = q.join(User, Booking.customer_id == User.id).filter(
                or_(User.full_name.ilike(like), User.email.ilike(like), Booking.reference.ilike(like))
            )

        total = q.count()
        page = max(1, page)
        items = (
            q.order_by(Booking.start_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, booking: Booking) -> Booking:
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def update(self, booking: Booking) -> Booking:
        self.db.commit()
        self.db.refresh(booking)
        return booking
