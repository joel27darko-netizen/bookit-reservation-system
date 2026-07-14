"""
Regression tests for the bookings-list filter bug (empty-string
resource_id 422ing) and pagination correctness.
"""
from datetime import timedelta

from tests.conftest import login, tomorrow_at


def _create_booking(client, resource_id, start, end):
    return client.post(
        "/bookings/create",
        data={"resource_id": resource_id, "start_time": start.isoformat(), "end_time": end.isoformat(), "party_size": 1},
        follow_redirects=False,
    )


def test_empty_resource_id_filter_does_not_422(client, admin_user, sample_resource):
    """Regression: selecting 'All Resources' used to send resource_id=''
    which FastAPI's int coercion rejected with a 422."""
    login(client, "admin@test.com", "adminpass123")
    resp = client.get("/bookings?resource_id=&status=&date_from=&date_to=")
    assert resp.status_code == 200


def test_empty_status_filter_does_not_422(client, admin_user):
    login(client, "admin@test.com", "adminpass123")
    resp = client.get("/bookings?status=")
    assert resp.status_code == 200


def test_resource_id_filter_scopes_results(client, admin_user, customer_user, sample_resource, db_session):
    from app.models.resource import Resource, ResourceTypeEnum
    other_resource = Resource(
        name="Other Room", type=ResourceTypeEnum.room, capacity=2,
        price_per_hour=10.0, open_time="00:00", close_time="23:59",
    )
    db_session.add(other_resource)
    db_session.commit()
    db_session.refresh(other_resource)

    login(client, "admin@test.com", "adminpass123")
    _create_booking(client, sample_resource.id, tomorrow_at(9), tomorrow_at(10))
    _create_booking(client, other_resource.id, tomorrow_at(9), tomorrow_at(10))

    resp = client.get(f"/bookings?resource_id={sample_resource.id}")
    # Resource names also appear in two <select> dropdowns elsewhere on the
    # page (the filter bar and the "New Booking" modal) regardless of
    # filtering, so scope the assertion to just the results table body.
    tbody = resp.text.split('<tbody>')[1].split('</tbody>')[0]
    assert sample_resource.name in tbody
    assert other_resource.name not in tbody


def test_calendar_events_empty_resource_id_does_not_422(client, admin_user):
    login(client, "admin@test.com", "adminpass123")
    resp = client.get("/calendar/events?resource_id=")
    assert resp.status_code == 200


def test_pagination_splits_results_correctly(client, admin_user, sample_resource):
    login(client, "admin@test.com", "adminpass123")
    base = tomorrow_at(0)
    # Create 15 bookings on distinct days so none overlap.
    for i in range(15):
        day_start = base + timedelta(days=i)
        _create_booking(client, sample_resource.id, day_start.replace(hour=9), day_start.replace(hour=10))

    page1 = client.get("/bookings?page=1")
    assert page1.status_code == 200
    assert "Page 1 of 2" in page1.text

    page2 = client.get("/bookings?page=2")
    assert page2.status_code == 200
    assert "Page 2 of 2" in page2.text


def test_pagination_preserves_filters_in_links(client, admin_user, sample_resource):
    login(client, "admin@test.com", "adminpass123")
    base = tomorrow_at(0)
    for i in range(15):
        day_start = base + timedelta(days=i)
        _create_booking(client, sample_resource.id, day_start.replace(hour=9), day_start.replace(hour=10))

    resp = client.get(f"/bookings?resource_id={sample_resource.id}&page=1")
    assert f"resource_id={sample_resource.id}&amp;page=2" in resp.text


def test_customer_search_by_name(client, admin_user, customer_user, other_customer, sample_resource):
    login(client, "admin@test.com", "adminpass123")
    # Admin books on behalf of the customer explicitly via customer_id,
    # otherwise the booking would default to the admin's own account.
    client.post(
        "/bookings/create",
        data={
            "resource_id": sample_resource.id,
            "start_time": tomorrow_at(9).isoformat(),
            "end_time": tomorrow_at(10).isoformat(),
            "party_size": 1,
            "customer_id": customer_user.id,
        },
        follow_redirects=False,
    )

    resp = client.get(f"/bookings?q={customer_user.full_name.split()[0]}")
    assert resp.status_code == 200
    assert customer_user.full_name in resp.text
    assert other_customer.full_name not in resp.text


def test_bookings_page_accepts_calendar_click_params(client, customer_user):
    """Regression test for the 'click a day on the calendar to book' feature:
    the bookings page must accept open_new/date/time query params without
    erroring, since the calendar redirects here with them set."""
    login(client, "customer@test.com", "custpass123")
    resp = client.get("/bookings?open_new=1&date=2026-12-01&time=14:30")
    assert resp.status_code == 200
    assert "open_new" in resp.text  # the prefill script reads it client-side


def test_calendar_page_has_date_click_handler(client, customer_user):
    login(client, "customer@test.com", "custpass123")
    resp = client.get("/calendar")
    assert resp.status_code == 200
    assert "dateClick" in resp.text
