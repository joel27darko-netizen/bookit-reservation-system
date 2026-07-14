"""
Shared pytest fixtures.

Each test function gets a fresh in-memory SQLite database (via a
StaticPool so the single connection is shared across the TestClient's
threadpool) and a TestClient with app.database.get_db overridden to use
it. This keeps tests fast, isolated, and independent of any real
bookit.db on disk.
"""
import pytest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User, RoleEnum
from app.models.resource import Resource, ResourceTypeEnum
from app.core import rate_limit as rate_limit_module


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    # Rate-limit state is a module-level dict shared across tests unless
    # cleared -- reset it so one test's failed logins don't lock out another.
    rate_limit_module._attempts.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(db_session, name, email, password, role):
    user = User(full_name=name, email=email, hashed_password=hash_password(password), role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_user(db_session):
    return _make_user(db_session, "Ada Admin", "admin@test.com", "adminpass123", RoleEnum.admin)


@pytest.fixture()
def staff_user(db_session):
    return _make_user(db_session, "Sam Staff", "staff@test.com", "staffpass123", RoleEnum.staff)


@pytest.fixture()
def customer_user(db_session):
    return _make_user(db_session, "Casey Customer", "customer@test.com", "custpass123", RoleEnum.customer)


@pytest.fixture()
def other_customer(db_session):
    return _make_user(db_session, "Jordan Other", "jordan@test.com", "custpass123", RoleEnum.customer)


@pytest.fixture()
def sample_resource(db_session):
    resource = Resource(
        name="Conference Room A",
        type=ResourceTypeEnum.room,
        location="Ground Floor",
        capacity=4,
        price_per_hour=20.0,
        open_time="00:00",
        close_time="23:59",
    )
    db_session.add(resource)
    db_session.commit()
    db_session.refresh(resource)
    return resource


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=False)


def tomorrow_at(hour, minute=0):
    d = datetime.now() + timedelta(days=1)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


def soon_same_day(minutes_from_now=30, duration_minutes=60):
    """
    A start/end pair that's "soon" (inside the default 2h cancellation
    notice window) but guaranteed not to cross midnight -- avoids flaky
    failures when the suite happens to run late at night, since resources
    require start/end to fall on the same calendar day.
    """
    now = datetime.now()
    start = now + timedelta(minutes=minutes_from_now)
    end = start + timedelta(minutes=duration_minutes)
    if start.date() != now.date() or end.date() != now.date():
        # Too close to midnight for this offset to stay same-day -- use a
        # short, safely-in-range window before end of day instead.
        start = now.replace(hour=23, minute=15, second=0, microsecond=0)
        if start <= now:
            start = now + timedelta(minutes=2)
        end = min(start + timedelta(minutes=duration_minutes), now.replace(hour=23, minute=58))
    return start, end


@pytest.fixture(autouse=True, scope="session")
def _cleanup_stray_db_file():
    # The app's startup event calls Base.metadata.create_all() against the
    # real (non-test) engine too, which touches a bookit.db file on disk.
    # Tests never read/write through it (get_db is overridden), but tidy
    # up afterwards so running the suite doesn't leave test artifacts.
    yield
    import os
    if os.path.exists("bookit.db") and os.path.getsize("bookit.db") <= 65536:
        try:
            os.remove("bookit.db")
        except OSError:
            pass
