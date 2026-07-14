"""
Role-based access control: each protected route should be reachable by
the roles it's meant for and blocked (403) for everyone else. Also
covers the customer data-scoping fix (no cross-customer leakage).
"""
from tests.conftest import login


ADMIN_ONLY = ["/users", "/audit-log"]
STAFF_AND_ADMIN_ONLY = ["/checkin", "/reports", "/notifications"]
ANY_LOGGED_IN = ["/dashboard", "/calendar", "/resources", "/bookings", "/profile"]


def test_admin_only_routes_block_customer(client, admin_user, customer_user):
    login(client, "customer@test.com", "custpass123")
    for path in ADMIN_ONLY:
        resp = client.get(path)
        assert resp.status_code == 403, f"{path} should be 403 for customer"


def test_admin_only_routes_block_staff(client, admin_user, staff_user):
    login(client, "staff@test.com", "staffpass123")
    for path in ADMIN_ONLY:
        resp = client.get(path)
        assert resp.status_code == 403, f"{path} should be 403 for staff"


def test_admin_only_routes_allow_admin(client, admin_user):
    login(client, "admin@test.com", "adminpass123")
    for path in ADMIN_ONLY:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} should be 200 for admin"


def test_staff_routes_block_customer(client, staff_user, customer_user):
    login(client, "customer@test.com", "custpass123")
    for path in STAFF_AND_ADMIN_ONLY:
        resp = client.get(path)
        assert resp.status_code == 403, f"{path} should be 403 for customer"


def test_staff_routes_allow_staff_and_admin(client, staff_user, admin_user):
    login(client, "staff@test.com", "staffpass123")
    for path in STAFF_AND_ADMIN_ONLY:
        assert client.get(path).status_code == 200

    login(client, "admin@test.com", "adminpass123")
    for path in STAFF_AND_ADMIN_ONLY:
        assert client.get(path).status_code == 200


def test_any_logged_in_user_can_reach_shared_routes(client, customer_user):
    login(client, "customer@test.com", "custpass123")
    for path in ANY_LOGGED_IN:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} should be 200 for any logged-in user"


def test_unauthenticated_user_redirected_to_login(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"


def test_customer_cannot_see_other_customers_bookings(client, customer_user, other_customer, sample_resource, db_session):
    """Regression test for the dashboard/calendar data-scoping fix."""
    from datetime import datetime, timedelta
    from app.models.booking import Booking, BookingStatusEnum

    start = datetime.now() + timedelta(days=1)
    end = start + timedelta(hours=1)
    other_booking = Booking(
        resource_id=sample_resource.id, customer_id=other_customer.id,
        start_time=start, end_time=end, status=BookingStatusEnum.confirmed,
        party_size=1, total_price=20.0,
    )
    db_session.add(other_booking)
    db_session.commit()

    login(client, "customer@test.com", "custpass123")
    dashboard = client.get("/dashboard")
    assert other_customer.full_name not in dashboard.text

    calendar_events = client.get("/calendar/events").json()
    customers_visible = {e["extendedProps"]["customer"] for e in calendar_events}
    assert other_customer.full_name not in customers_visible


def test_customer_dashboard_has_no_business_metrics(client, customer_user):
    login(client, "customer@test.com", "custpass123")
    resp = client.get("/dashboard")
    assert "revenue" not in resp.text.lower()
    assert "occupancy" not in resp.text.lower()


def test_admin_dashboard_has_business_metrics(client, admin_user):
    login(client, "admin@test.com", "adminpass123")
    resp = client.get("/dashboard")
    assert "revenue" in resp.text.lower()
