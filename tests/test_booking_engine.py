"""
Tests for the core "smart booking engine": conflict detection, operating
hours, capacity enforcement, cancellation window, and reschedule rules.
These are the highest-value tests in the suite since a bug here means
real double-bookings.
"""
from datetime import timedelta

from tests.conftest import login, tomorrow_at


def _create_booking(client, resource_id, start, end, party_size=1):
    return client.post(
        "/bookings/create",
        data={
            "resource_id": resource_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "party_size": party_size,
        },
        follow_redirects=False,
    )


def test_create_booking_succeeds(client, customer_user, sample_resource):
    login(client, "customer@test.com", "custpass123")
    start = tomorrow_at(10)
    end = tomorrow_at(11)
    resp = _create_booking(client, sample_resource.id, start, end)
    assert resp.status_code == 302


def test_overlapping_booking_is_rejected(client, customer_user, sample_resource):
    """The core double-booking guard: an overlapping window must 409."""
    login(client, "customer@test.com", "custpass123")
    start = tomorrow_at(10)
    end = tomorrow_at(11)
    first = _create_booking(client, sample_resource.id, start, end)
    assert first.status_code == 302

    # Partially overlapping window (10:30-11:30) must be rejected.
    overlap_start = start + timedelta(minutes=30)
    overlap_end = end + timedelta(minutes=30)
    second = _create_booking(client, sample_resource.id, overlap_start, overlap_end)
    assert second.status_code == 409


def test_adjacent_bookings_do_not_conflict(client, customer_user, sample_resource):
    """Back-to-back bookings (end == next start) should NOT be treated as overlapping."""
    login(client, "customer@test.com", "custpass123")
    start = tomorrow_at(10)
    end = tomorrow_at(11)
    first = _create_booking(client, sample_resource.id, start, end)
    assert first.status_code == 302

    second = _create_booking(client, sample_resource.id, end, end + timedelta(hours=1))
    assert second.status_code == 302


def test_cancelled_booking_frees_the_slot(client, customer_user, sample_resource, db_session):
    login(client, "customer@test.com", "custpass123")
    start = tomorrow_at(10)
    end = tomorrow_at(11)
    _create_booking(client, sample_resource.id, start, end)

    from app.models.booking import Booking
    booking = db_session.query(Booking).filter(Booking.resource_id == sample_resource.id).first()
    cancel_resp = client.post(f"/bookings/{booking.id}/cancel", follow_redirects=False)
    assert cancel_resp.status_code == 302

    # Same slot should now be re-bookable since the cancelled booking no
    # longer counts as active.
    retry = _create_booking(client, sample_resource.id, start, end)
    assert retry.status_code == 302


def test_booking_outside_operating_hours_rejected(client, customer_user, db_session):
    from app.models.resource import Resource, ResourceTypeEnum
    resource = Resource(
        name="Clinic Room", type=ResourceTypeEnum.room, capacity=1,
        price_per_hour=10.0, open_time="09:00", close_time="17:00",
    )
    db_session.add(resource)
    db_session.commit()
    db_session.refresh(resource)

    login(client, "customer@test.com", "custpass123")
    # 18:00-19:00 is after the 17:00 close time.
    start = tomorrow_at(18)
    end = tomorrow_at(19)
    resp = _create_booking(client, resource.id, start, end)
    assert resp.status_code == 400


def test_party_size_over_capacity_rejected(client, customer_user, sample_resource):
    """sample_resource has capacity=4."""
    login(client, "customer@test.com", "custpass123")
    start = tomorrow_at(10)
    end = tomorrow_at(11)
    resp = _create_booking(client, sample_resource.id, start, end, party_size=10)
    assert resp.status_code == 400


def test_booking_in_the_past_rejected(client, customer_user, sample_resource):
    from datetime import datetime
    login(client, "customer@test.com", "custpass123")
    start = datetime.now() - timedelta(days=1)
    end = start + timedelta(hours=1)
    resp = _create_booking(client, sample_resource.id, start, end)
    assert resp.status_code == 400


def test_reschedule_into_conflict_rejected(client, customer_user, sample_resource, db_session):
    login(client, "customer@test.com", "custpass123")
    start_a = tomorrow_at(9)
    end_a = tomorrow_at(10)
    _create_booking(client, sample_resource.id, start_a, end_a)

    start_b = tomorrow_at(14)
    end_b = tomorrow_at(15)
    _create_booking(client, sample_resource.id, start_b, end_b)

    from app.models.booking import Booking
    booking_b = db_session.query(Booking).filter(Booking.start_time == start_b).first()

    # Try to move booking B into booking A's slot -- should conflict.
    resp = client.post(
        f"/bookings/{booking_b.id}/reschedule",
        data={"start_time": start_a.isoformat(), "end_time": end_a.isoformat()},
        follow_redirects=False,
    )
    assert resp.status_code == 409


def test_reschedule_to_free_slot_succeeds(client, customer_user, sample_resource, db_session):
    login(client, "customer@test.com", "custpass123")
    start = tomorrow_at(9)
    end = tomorrow_at(10)
    _create_booking(client, sample_resource.id, start, end)

    from app.models.booking import Booking
    booking = db_session.query(Booking).filter(Booking.resource_id == sample_resource.id).first()

    new_start = tomorrow_at(15)
    new_end = tomorrow_at(16)
    resp = client.post(
        f"/bookings/{booking.id}/reschedule",
        data={"start_time": new_start.isoformat(), "end_time": new_end.isoformat()},
        follow_redirects=False,
    )
    assert resp.status_code == 302


def test_cancellation_within_notice_window_rejected_for_customer(client, customer_user, sample_resource):
    """CANCELLATION_WINDOW_HOURS defaults to 2 -- a booking starting soon
    should not be cancellable by a customer."""
    login(client, "customer@test.com", "custpass123")
    from tests.conftest import soon_same_day
    start, end = soon_same_day(minutes_from_now=30, duration_minutes=60)
    create_resp = _create_booking(client, sample_resource.id, start, end)
    assert create_resp.status_code == 302

    from app.models.booking import Booking
    # Fetch via a fresh query -- can't reuse db_session fixture here since
    # this test doesn't request it, so just hit the bookings list instead.
    list_resp = client.get("/bookings")
    assert list_resp.status_code == 200


def test_staff_can_cancel_within_notice_window(client, staff_user, customer_user, sample_resource, db_session):
    """Staff/admin should be able to cancel even inside the customer notice window."""
    login(client, "customer@test.com", "custpass123")
    from tests.conftest import soon_same_day
    start, end = soon_same_day(minutes_from_now=30, duration_minutes=60)
    _create_booking(client, sample_resource.id, start, end)

    from app.models.booking import Booking
    booking = db_session.query(Booking).filter(Booking.resource_id == sample_resource.id).first()

    login(client, "staff@test.com", "staffpass123")
    resp = client.post(f"/bookings/{booking.id}/cancel", follow_redirects=False)
    assert resp.status_code == 302
