"""
Dashboard service: aggregates booking/resource data into the metrics
shown on the dashboard.

Staff/admin get business metrics (occupancy, revenue, all upcoming
bookings). Customers get a personal view scoped to their own bookings --
revenue and occupancy are operational figures that shouldn't be exposed
to end customers, and "upcoming bookings" must never include other
customers' reservations.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatusEnum
from app.models.resource import Resource
from app.models.user import User, RoleEnum
from app.repositories.booking_repo import BookingRepository, ACTIVE_STATUSES
from app.repositories.resource_repo import ResourceRepository


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.booking_repo = BookingRepository(db)
        self.resource_repo = ResourceRepository(db)

    def summary(self, user: User, days_ahead: int = 7) -> Dict:
        """Dispatch to the business view (staff/admin) or personal view (customer)."""
        if user.role == RoleEnum.customer:
            return self._customer_summary(user, days_ahead)
        return self._business_summary(days_ahead)

    def _business_summary(self, days_ahead: int = 7) -> Dict:
        now = datetime.now()
        window_end = now + timedelta(days=days_ahead)

        resources = self.resource_repo.list_all(only_active=True)
        all_bookings = self.booking_repo.list_by_filters(date_from=now - timedelta(days=30))

        # Revenue: sum of completed/confirmed/checked-in bookings in the last 30 days.
        revenue_bookings = [b for b in all_bookings if b.status in ACTIVE_STATUSES]
        total_revenue = round(sum(b.total_price for b in revenue_bookings), 2)

        # Occupancy rate: booked-hours / available-hours across active resources for "today".
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        todays_bookings = [
            b for b in all_bookings
            if b.status in ACTIVE_STATUSES and b.start_time < today_end and b.end_time > today_start
        ]
        booked_hours = sum(
            (min(b.end_time, today_end) - max(b.start_time, today_start)).total_seconds() / 3600
            for b in todays_bookings
        )
        available_hours = 0.0
        for r in resources:
            oh, om = map(int, r.open_time.split(":"))
            ch, cm = map(int, r.close_time.split(":"))
            available_hours += max(0.0, (ch * 60 + cm - oh * 60 - om) / 60)
        occupancy_rate = round((booked_hours / available_hours) * 100, 1) if available_hours > 0 else 0.0

        upcoming = [
            b for b in all_bookings
            if b.status == BookingStatusEnum.confirmed and now <= b.start_time <= window_end
        ]
        upcoming.sort(key=lambda b: b.start_time)

        return {
            "view": "business",
            "total_resources": len(resources),
            "total_bookings_30d": len(all_bookings),
            "active_bookings": len([b for b in all_bookings if b.status == BookingStatusEnum.confirmed]),
            "occupancy_rate": occupancy_rate,
            "total_revenue_30d": total_revenue,
            "upcoming_bookings": upcoming[:10],
            "trend": self._revenue_trend(all_bookings, days=14),
        }

    @staticmethod
    def _revenue_trend(bookings: List[Booking], days: int = 14) -> Dict:
        """
        Daily revenue + booking-count series for the last `days` days, for
        the dashboard trend chart. Only counts bookings in ACTIVE_STATUSES
        (the same definition used for the headline revenue figure).
        """
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        buckets = {}
        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            buckets[day.date()] = {"revenue": 0.0, "count": 0}

        for b in bookings:
            if b.status not in ACTIVE_STATUSES:
                continue
            day = b.start_time.date()
            if day in buckets:
                buckets[day]["revenue"] += b.total_price
                buckets[day]["count"] += 1

        labels = [d.strftime("%b %d") for d in buckets.keys()]
        revenue = [round(v["revenue"], 2) for v in buckets.values()]
        counts = [v["count"] for v in buckets.values()]
        return {"labels": labels, "revenue": revenue, "counts": counts}

    def _customer_summary(self, user: User, days_ahead: int = 7) -> Dict:
        now = datetime.now()
        window_end = now + timedelta(days=days_ahead)

        # Scoped strictly to this customer -- no cross-customer data, no
        # revenue/occupancy figures that are operational, not personal.
        my_bookings = self.booking_repo.list_by_filters(customer_id=user.id)

        upcoming = [
            b for b in my_bookings
            if b.status == BookingStatusEnum.confirmed and now <= b.start_time <= window_end
        ]
        upcoming.sort(key=lambda b: b.start_time)

        next_booking = upcoming[0] if upcoming else None
        active_count = len([b for b in my_bookings if b.status == BookingStatusEnum.confirmed])
        completed_count = len([b for b in my_bookings if b.status == BookingStatusEnum.completed])

        return {
            "view": "customer",
            "active_bookings": active_count,
            "completed_bookings": completed_count,
            "next_booking": next_booking,
            "upcoming_bookings": upcoming[:10],
        }

    def calendar_events(self, resource_id: int = None, user: Optional[User] = None) -> List[Dict]:
        """
        Return bookings formatted for FullCalendar.js consumption.
        Customers only ever see their own bookings on the calendar.
        """
        filters = {}
        if resource_id:
            filters["resource_id"] = resource_id
        if user and user.role == RoleEnum.customer:
            filters["customer_id"] = user.id
        bookings = self.booking_repo.list_by_filters(**filters)

        color_map = {
            BookingStatusEnum.confirmed: "#147D6F",
            BookingStatusEnum.checked_in: "#6D4AA6",
            BookingStatusEnum.cancelled: "#74695D",
            BookingStatusEnum.completed: "#2A5C8A",
            BookingStatusEnum.no_show: "#B23A2E",
        }

        events = []
        for b in bookings:
            resource: Resource = b.resource
            events.append({
                "id": b.id,
                "title": f"{resource.name} - {b.customer.full_name}",
                "start": b.start_time.isoformat(),
                "end": b.end_time.isoformat(),
                "color": color_map.get(b.status, "#0d6efd"),
                "extendedProps": {
                    "reference": b.reference,
                    "status": b.status.value,
                    "resource": resource.name,
                    "customer": b.customer.full_name,
                },
            })
        return events
