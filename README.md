# BookIt

A booking and reservation system I built to work for pretty much any business that manages time slots and physical (or semi-physical) resources — hotel rooms, coworking desks, clinic equipment, meeting rooms, whatever. Instead of building something narrowly tied to "just hotels" or "just clinics," I focused on the actual hard problem underneath all of them: making sure two people can never book the same thing at the same time.

It's built with FastAPI on the backend, server-rendered HTML on the frontend (Jinja2 + Bootstrap, no separate JS framework), and it's got a real test suite behind it — not just something that looks nice in a demo.

## Why I built it this way

I wanted to actually practice a clean backend architecture instead of just throwing everything into one big file. So the app is split into layers:

- **Routers** just handle the web request/response — they don't know anything about business rules
- **Services** hold all the actual logic — this is where the booking conflict detection lives, where prices get calculated, where the rules about who can cancel what get enforced
- **Repositories** are the only part of the app that talk to the database
- **Models** are just the shape of the data

It felt like overkill at first for a project this size, but it paid off almost immediately — when I found a bug where customers could see other customers' bookings, I only had to fix it in one place (the service layer), not hunt through a dozen route handlers.

## What it actually does

- Three roles — **customer**, **staff**, **admin** — each seeing a different version of the app depending on what they're allowed to do
- Real-time availability checking, so you can't accidentally double-book a room
- Booking creation, rescheduling, and cancellation, each with their own rules (like a minimum notice period before you can cancel)
- A calendar view where you can literally click a day (or a specific time slot) and it takes you straight into a pre-filled booking form
- QR code check-in — every booking gets a QR code, and there's a simple scanner page for staff to check guests in
- CSV and PDF exports for reports (bookings, occupancy, revenue)
- An audit log tracking who did what
- A dashboard that shows different things depending on who's looking at it — staff and admins see revenue and occupancy, customers just see their own upcoming bookings (nobody else's business is anybody else's business)

## Getting it running

```bash
pip install -r requirements.txt
cp .env.example .env        # then open it and set a real SECRET_KEY
python seed.py               # creates the database and some demo data
uvicorn app.main:app --reload
```

Then go to `http://localhost:8000`. There are three demo accounts already set up so you can see what each role looks like:

| Role | Email | Password |
|---|---|---|
| Admin | admin@bookit.com | admin123 |
| Staff | staff@bookit.com | staff123 |
| Customer | customer@bookit.com | customer123 |

## Running the tests

```bash
pytest
```

There are 42 tests right now, covering the stuff I actually worried about breaking: the double-booking prevention logic, whether each role can see/do what it's supposed to, a couple of real bugs I found and fixed along the way (a filter that used to crash the page, a data leak where customers could see other customers' info), and the login rate limiter.

Every test runs against a completely separate in-memory database, so running the suite never touches whatever real data you've got in `bookit.db`.

## How the conflict detection actually works

This was the part I spent the most time getting right. A new booking conflicts with an existing one if:

```
existing.start_time < new.end_time AND existing.end_time > new.start_time
```

It's a pretty classic overlapping-intervals check, but the important part isn't the formula — it's *where* it runs. The frontend checks availability before you submit, just so you get instant feedback. But the real enforcement happens again on the server, right before the booking actually gets saved. That second check is what actually stops two people from grabbing the same slot if they both hit submit around the same time.

## What's still rough around the edges

Being honest about the current state:

- It uses SQLite by default, which is fine for development but you'd want Postgres for anything with real concurrent traffic
- The rate limiter and notification system are both in-memory, which works for a single server but wouldn't survive a multi-instance deployment without changes
- Email/SMS notifications are simulated (they show up in an in-app "outbox") rather than actually sending anything — hooking up a real provider like SendGrid or Twilio would be the next step if this ever needed to go live for real

## Stack

Python, FastAPI, SQLAlchemy, Alembic, Pydantic, Jinja2, Bootstrap 5, FullCalendar.js, Chart.js, pytest.

---

Built as a learning project to get more comfortable with backend architecture, real-time conflict handling, and actually testing the things that matter instead of just hoping they work.
