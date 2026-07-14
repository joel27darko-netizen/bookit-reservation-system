"""
Auth flow: registration, login success/failure, and the rate limiter
that guards against brute-force login attempts.
"""
from tests.conftest import login


def test_register_creates_customer_and_logs_in(client):
    resp = client.post(
        "/register",
        data={"full_name": "New Person", "email": "new@test.com", "password": "password123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/dashboard"


def test_register_duplicate_email_rejected(client, customer_user):
    resp = client.post(
        "/register",
        data={"full_name": "Duplicate", "email": "customer@test.com", "password": "password123"},
    )
    assert resp.status_code == 400


def test_login_wrong_password_fails(client, customer_user):
    resp = login(client, "customer@test.com", "wrongpassword")
    assert resp.status_code == 400


def test_login_correct_password_succeeds(client, customer_user):
    resp = login(client, "customer@test.com", "custpass123")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/dashboard"


def test_login_sets_httponly_cookie(client, customer_user):
    resp = login(client, "customer@test.com", "custpass123")
    set_cookie = resp.headers.get("set-cookie", "")
    assert "httponly" in set_cookie.lower()


def test_repeated_failed_logins_get_rate_limited(client, customer_user):
    """After MAX_ATTEMPTS (5) failures for the same email, further
    attempts should be rejected with 429 instead of re-checking the
    password, even if a later attempt happens to be correct."""
    for _ in range(5):
        resp = login(client, "customer@test.com", "wrongpassword")
        assert resp.status_code == 400

    locked_resp = login(client, "customer@test.com", "custpass123")
    assert locked_resp.status_code == 429


def test_logout_clears_session(client, customer_user):
    login(client, "customer@test.com", "custpass123")
    assert client.get("/dashboard").status_code == 200

    client.get("/logout", follow_redirects=False)
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"
