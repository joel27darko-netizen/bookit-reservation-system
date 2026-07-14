# BookIt — Booking & Reservation Management System

A full-stack reservation platform suitable for hotels, coworking spaces, clinics,
or meeting rooms. Built with FastAPI + SQLAlchemy + Jinja2 + Bootstrap 5,
following a clean layered architecture.

## Design

The UI uses a custom design system (`app/static/css/style.css`) built around one
idea: **a reservation is a ticket.** Booking rows render as perforated ticket
stubs — a colored spine for status, a punched divider, a monospace reference
code — instead of generic dashboard rows. The rest of the app (sidebar nav,
stat cards, resource tiles, forms, tables) follows the same token system:
Space Grotesk for headings, Inter for body text, IBM Plex Mono for codes and
prices, and a cobalt-indigo accent (`#3654FF`) against a clean off-white
background. Fully responsive down to mobile (sidebar collapses to a horizontal
tab bar), with visible keyboard focus states and `prefers-reduced-motion` support.

## Features

- **Auth & RBAC** — JWT in httpOnly cookie, three roles (customer, staff, admin)
- **Resource management** — rooms, tables, equipment, or services with capacity,
  location, hourly pricing, and operating hours
- **Smart booking engine** — real-time availability checks, overlap/conflict
  detection, creation, rescheduling, cancellation (with a configurable
  cancellation-notice window)
- **Dashboard** — occupancy rate, revenue (30-day), upcoming bookings
- **Calendar view** — FullCalendar.js month/week/day views, color-coded by status
- **QR check-in** — generates a QR per booking; a "Simulated Scanner" page lets
  staff paste/type the payload to check guests in
- **Notifications** — simulated email/SMS outbox (visible in-app, since no real
  provider is wired up)
- **Reports** — CSV and PDF export for bookings summary, occupancy, and revenue
- **Search & filters** — by resource, status, date range, customer
- **Audit log** — every booking/resource/user mutation is recorded

## Architecture

Layered design, each layer only talks to the one below it:

```
Routers (FastAPI endpoints, request/response only)
   ↓
Services (business rules: availability engine, pricing, RBAC checks, audit, notifications)
   ↓
Repositories (pure SQLAlchemy queries, no business logic)
   ↓
Models (SQLAlchemy ORM tables)
```

```
app/
  main.py            FastAPI app, startup, global error handlers, router wiring
  config.py          Settings (env-driven)
  database.py         Engine/session/Base
  models/             SQLAlchemy models: User, Resource, Booking, AuditLog
  schemas/             Pydantic request/response validation
  core/
    security.py        Password hashing + JWT encode/decode
    deps.py             get_current_user, require_roles(...) RBAC dependency
  repositories/        Raw DB queries (UserRepository, ResourceRepository, ...)
  services/
    auth_service.py       register/login
    resource_service.py    resource CRUD + audit
    booking_service.py     ★ the "smart booking engine": availability, conflicts,
                             pricing, reschedule/cancel rules
    dashboard_service.py    occupancy/revenue aggregation, calendar events
    report_service.py       CSV/PDF generation
    qr_service.py           QR code generation/decoding
    notification_service.py simulated email/SMS outbox
    audit_service.py        audit log writer
  routers/            Thin endpoints per feature (auth, resources, bookings,
                       dashboard, reports, checkin, users)
  templates/           Jinja2 + Bootstrap 5 UI
  static/              CSS/JS (FullCalendar wiring, availability widget)
alembic/               Migration environment (autogenerate-ready off app/models)
seed.py                Demo data: 3 users, 6 resources, sample bookings
```

### Why this split works well here
- The **booking engine's conflict-detection logic** (`BookingService.is_available`,
  `find_overlapping` in `BookingRepository`) is isolated and unit-testable
  without touching HTTP concerns.
- **RBAC** is a single reusable dependency (`require_roles(...)`), not scattered
  `if role == ...` checks in every route.
- Swapping SQLite → PostgreSQL is a one-line change in `.env` (`DATABASE_URL`);
  nothing else in the codebase references the driver.

## Availability / conflict-detection logic

A resource is "double-booked" if any **active** booking (`confirmed`,
`checked_in`, or `completed`) on the same resource overlaps the requested
`[start, end)` window:

```python
existing.start_time < new.end_time AND existing.end_time > new.start_time
```

This runs both when the UI asks "is this slot free?" (`GET /resources/{id}/availability`)
and again authoritatively inside `create_booking`/`reschedule_booking` before
committing — so even concurrent requests can't create an overlap that slips
past the UI check.

## Getting started

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) copy and edit environment config
cp .env.example .env   # set SECRET_KEY, DATABASE_URL, etc.

# 3a. Quick start (dev): let the app auto-create tables + seed demo data
python seed.py

# 3b. Or, for a production-style setup, use Alembic migrations instead:
alembic revision --autogenerate -m "init"
alembic upgrade head

# 4. Run the server
uvicorn app.main:app --reload

# 5. Open http://localhost:8000
```

### Demo accounts (created by seed.py)

| Role     | Email               | Password    |
|----------|---------------------|-------------|
| Admin    | admin@bookit.com    | admin123    |
| Staff    | staff@bookit.com    | staff123    |
| Customer | customer@bookit.com | customer123 |

### Switching to PostgreSQL

Set in `.env`:
```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/bookit
```
Install `psycopg2-binary`, then run `alembic upgrade head` instead of relying
on the dev auto-create-tables behavior.

## Testing

The test suite (`tests/`) covers the areas most likely to break silently:
booking conflict detection, RBAC enforcement, the filter/pagination
regression, auth + rate limiting, and reports/notifications/QR check-in.
Each test runs against an isolated in-memory SQLite database, so it never
touches your real `bookit.db`.

```bash
pip install -r requirements.txt   # includes pytest + httpx
pytest                             # or: pytest -v for per-test output
```

40 tests, ~30s. Notably: `test_bookings_filters.py` locks in the fix for
the empty-string `resource_id=""` 422 bug, and `test_rbac.py` locks in
the customer dashboard/calendar data-scoping fix (no cross-customer
booking data leakage).

## Key endpoints

| Method | Path                                  | Purpose                              |
|--------|----------------------------------------|---------------------------------------|
| POST   | `/register`, `/login`, `/logout`       | Auth                                  |
| GET    | `/dashboard`                            | Metrics summary                       |
| GET    | `/calendar`, `/calendar/events`        | FullCalendar page + JSON event feed   |
| GET/POST | `/resources`, `/resources/create`    | Browse / manage resources             |
| GET    | `/resources/{id}/availability?day=`    | Real-time slot availability (JSON)    |
| GET/POST | `/bookings`, `/bookings/create`      | Search/filter + create bookings       |
| POST   | `/bookings/{id}/cancel`                 | Cancel (enforces notice window)       |
| POST   | `/bookings/{id}/reschedule`             | Reschedule (re-checks conflicts)      |
| GET    | `/bookings/{id}/qr`                     | QR code for check-in                  |
| GET/POST | `/checkin`, `/checkin/scan`          | Simulated QR scanner                  |
| GET    | `/reports/{type}/csv`, `/reports/{type}/pdf` | Export (`bookings`,`occupancy`,`revenue`) |
| GET    | `/notifications`                        | Simulated email/SMS outbox            |
| GET    | `/audit-log`                            | Admin-only action trail               |
| GET/POST | `/users`, `/users/{id}/role`          | Admin-only role management            |

## Notes / production hardening ideas

- Rotate `SECRET_KEY` and move it out of source control (`.env`, secrets manager)
- Add rate limiting on `/login` and `/register`
- Wire `NotificationService` to a real provider (SES/SendGrid, Twilio)
- Add row-level locking or a unique constraint + retry loop around booking
  creation for very high-concurrency resources
- Add pagination to `/bookings` and `/audit-log` for large datasets
