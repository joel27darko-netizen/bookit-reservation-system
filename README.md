# BookIt

**A real-time booking and reservation engine built to solve the one problem every scheduling system has to get right: never letting two people book the same thing at the same time.**

Built with FastAPI, SQLAlchemy, and a clean layered architecture — designed to work equally well for hotels, coworking spaces, clinics, or meeting rooms, because the hard part (conflict-free scheduling, role-based access, auditability) is the same problem underneath all of them.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-teal)
![Tests](https://img.shields.io/badge/tests-42%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## The problem this actually solves

Booking systems look simple until two people try to reserve the same room at the same time, or a customer cancels ten seconds before their appointment, or a "logged in" user turns out to be able to see data that isn't theirs. This project treats those as first-class problems, not edge cases bolted on later:

- **Conflict detection runs twice** — once client-side for instant feedback, and again authoritatively at the database layer right before commit, so a race between two simultaneous requests can't create a double-booking
- **Role-based access control** isn't `if role == "admin"` scattered through route handlers — it's a single reusable dependency (`require_roles(...)`) enforced consistently across every protected endpoint
- **Data scoping is enforced at the query level**, not just the UI level — a customer's dashboard and calendar are filtered server-side by `customer_id`, so there's no code path where one customer's bookings leak into another's view
- **Every mutation is audited** — booking creation, cancellation, rescheduling, resource edits, and role changes all write to an immutable audit log

## Architecture

Strict separation of concerns, each layer depending only on the one below it:

```
Routers      → HTTP in, HTTP out. No business logic.
Services     → All business rules live here (the booking engine, pricing, RBAC, audit).
Repositories → Raw database queries. Nothing else.
Models       → Data shape only.
```

```
app/
├── main.py                    FastAPI app, security headers, global error handling
├── config.py                  Environment-driven settings (pydantic-settings)
├── database.py                SQLAlchemy engine/session
├── models/                    User, Resource, Booking, AuditLog
├── schemas/                   Pydantic request/response validation
├── core/
│   ├── security.py              JWT + bcrypt password hashing
│   ├── deps.py                  get_current_user, require_roles() RBAC guard
│   └── rate_limit.py            Brute-force login protection
├── repositories/               Paginated + unpaginated query variants
├── services/
│   ├── booking_service.py        ← the booking engine: availability, conflicts,
│   │                                pricing, reschedule/cancel rules
│   ├── dashboard_service.py      Role-scoped metrics + calendar feed
│   ├── report_service.py         CSV/PDF generation
│   ├── qr_service.py             QR generation/decoding
│   ├── notification_service.py   Simulated email/SMS outbox
│   └── audit_service.py          Immutable action log
├── routers/                    Thin endpoints, one file per feature
├── templates/                  Jinja2 + Bootstrap 5, zero client-side framework
└── static/                     CSS + vanilla JS
tests/                          42 tests, isolated in-memory database per run
alembic/                        Schema migrations
```

This isn't architecture for architecture's sake — it paid for itself directly. A real data-leak bug (customers could see other customers' bookings on the dashboard) was fixed in exactly one file, because the scoping logic lived in a single service method rather than being duplicated across route handlers.

## The conflict-detection algorithm

```python
existing.start_time < new.end_time AND existing.end_time > new.start_time
```

The classic interval-overlap check — but the interesting engineering decision isn't the formula, it's **where it's enforced**. The UI checks availability before submission purely for user feedback. The service layer re-checks it again, inside the same transaction that creates the booking, which is what actually closes the race condition between two concurrent requests. Client-side validation is a UX nicety; server-side validation is the only one that's actually a guarantee.

## Features

| | |
|---|---|
| **Auth** | JWT in httpOnly cookies, bcrypt hashing, rate-limited login/registration |
| **RBAC** | Customer / Staff / Admin, each with a genuinely different view of the app |
| **Booking engine** | Real-time availability, conflict detection, reschedule, cancellation with a configurable notice window |
| **Calendar** | FullCalendar.js month/week/day views — click any day or time slot to start a pre-filled booking |
| **Check-in** | Per-booking QR codes with a working scan-and-check-in flow |
| **Reporting** | CSV + PDF export for bookings, occupancy, and revenue |
| **Dashboard** | Role-scoped — staff/admin see revenue, occupancy, and a 14-day trend chart; customers see only their own bookings |
| **Audit log** | Every mutating action, attributed and timestamped |
| **Search & pagination** | By resource, status, date range, and customer name |

## Getting started

```bash
git clone https://github.com/joel27darko-netizen/bookit-reservation-system.git
cd bookit-reservation-system
pip install -r requirements.txt
cp .env.example .env        # set a real SECRET_KEY before deploying anywhere
python seed.py               # creates the DB and demo data
uvicorn app.main:app --reload
```

Open `http://localhost:8000`. Demo accounts are seeded automatically:

| Role | Email | Password |
|---|---|---|
| Admin | admin@bookit.com | admin123 |
| Staff | staff@bookit.com | staff123 |
| Customer | customer@bookit.com | customer123 |

### Using PostgreSQL instead of SQLite

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/bookit
```
Install `psycopg2-binary`, then run `alembic upgrade head` instead of relying on dev auto-create.

## Testing

```bash
pytest
```

**42 tests**, each running against an isolated in-memory database — never touching real data. This isn't a token test file; it's the thing that catches regressions before they ship:

- Overlap detection, adjacent (non-conflicting) bookings, capacity limits, operating-hours enforcement, past-date rejection
- Every protected route checked against every role
- Two locked-in regression tests for real bugs that happened during development: a filter that 422'd on empty query params, and a cross-customer data leak on the dashboard
- Rate limiting, auth flows, CSV/PDF export permissions, and the full QR check-in cycle

## Tech stack

**Backend:** FastAPI · SQLAlchemy · Pydantic · Alembic · python-jose · passlib/bcrypt
**Frontend:** Jinja2 · Bootstrap 5 · FullCalendar.js · Chart.js · vanilla JS (no build step, no framework)
**Testing:** pytest · httpx
**Reports:** ReportLab (PDF) · native CSV streaming
**Check-in:** qrcode · Pillow

## Known limitations

Being upfront about what this isn't, yet:

- SQLite by default — fine for development, needs PostgreSQL for real concurrent load
- Rate limiting and the notification outbox are in-memory, so they're per-process — a multi-instance deployment would need Redis behind both
- Notifications are simulated (visible in an in-app outbox) rather than wired to a real provider — swapping in SES/SendGrid/Twilio is a contained change, not a rearchitecture

## License

MIT.
