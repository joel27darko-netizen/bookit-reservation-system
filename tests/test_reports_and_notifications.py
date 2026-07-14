"""
Reports (CSV/PDF export) and the simulated notification outbox.
"""
from tests.conftest import login, tomorrow_at


def test_csv_export_requires_staff_or_admin(client, customer_user):
    login(client, "customer@test.com", "custpass123")
    resp = client.get("/reports/bookings/csv")
    assert resp.status_code == 403


def test_csv_export_succeeds_for_admin(client, admin_user):
    login(client, "admin@test.com", "adminpass123")
    resp = client.get("/reports/bookings/csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")


def test_pdf_export_succeeds_for_admin(client, admin_user):
    login(client, "admin@test.com", "adminpass123")
    resp = client.get("/reports/revenue/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


def test_booking_confirmation_appears_in_notification_outbox(client, admin_user, sample_resource):
    login(client, "admin@test.com", "adminpass123")
    client.post(
        "/bookings/create",
        data={
            "resource_id": sample_resource.id,
            "start_time": tomorrow_at(10).isoformat(),
            "end_time": tomorrow_at(11).isoformat(),
            "party_size": 1,
        },
        follow_redirects=False,
    )
    resp = client.get("/notifications")
    assert sample_resource.name in resp.text


def test_qr_checkin_flow(client, admin_user, sample_resource, db_session):
    login(client, "admin@test.com", "adminpass123")
    client.post(
        "/bookings/create",
        data={
            "resource_id": sample_resource.id,
            "start_time": tomorrow_at(10).isoformat(),
            "end_time": tomorrow_at(11).isoformat(),
            "party_size": 1,
        },
        follow_redirects=False,
    )
    from app.models.booking import Booking
    booking = db_session.query(Booking).filter(Booking.resource_id == sample_resource.id).first()

    qr_page = client.get(f"/bookings/{booking.id}/qr")
    assert qr_page.status_code == 200

    checkin_resp = client.post("/checkin/scan", data={"payload": f"BOOKIT:{booking.reference}"})
    assert checkin_resp.status_code == 200
    assert "Checked in" in checkin_resp.text

    # Scanning the same booking again should fail cleanly, not double-check-in.
    second_scan = client.post("/checkin/scan", data={"payload": f"BOOKIT:{booking.reference}"})
    assert "Already checked in" in second_scan.text or "already checked in" in second_scan.text.lower()
