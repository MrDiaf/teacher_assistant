# M1 — Calendar backend foundation

- [x] This milestone

## Outcome

Establish the database, service, repository, schemas, and versioned API needed
to manage calendars and events without requiring a calendar grid or Codex.

This milestone is the base for every later Calendar and Assistant milestone.
The application is single-owner, timestamps for timed events are stored
consistently in UTC, and the owner timezone is used for display.

## Dependencies and boundaries

- Preserve the existing Teacher Assistant application shell.
- Use the existing FastAPI, SQLAlchemy, Alembic, and test patterns.
- Keep business rules in calendar services, not routes or models.
- Do not implement frontend calendar views, ICS import, or Codex integration.
- Treat `is_read_only` as a hard backend permission boundary.

## Required data

A calendar includes at least ID, name, description, color, visibility,
read-only state, source type, and timestamps. Initial source types are `local`
and `ics_import`; new local calendars default writable.

An event includes at least ID, calendar ID, title, description, location,
start/end, all-day state, timezone, recurrence fields, status, and timestamps.
Initial statuses are `confirmed`, `tentative`, and `cancelled`.

## Completed checklist

- [x] Inspect and preserve the existing application shell.
- [x] Add Calendar and Event database models.
- [x] Add Alembic migrations.
- [x] Add calendar and event repositories and services.
- [x] Add API schemas and versioned routes.
- [x] Enforce read-only calendars in backend mutation paths.
- [x] Add backend CRUD and permission tests.

## Acceptance criteria

- Calendars and events can be created, read, updated, and deleted through the
  API where permissions allow.
- Attempts to create, update, move, resize, or delete an event on a read-only
  calendar fail with a clear permission error.
- Calendar business logic is not embedded in routes or SQLAlchemy models.
- Relevant backend tests pass.
- No calendar grid or Codex integration is required.

## Completion evidence and implementation areas

- Migration: `backend/alembic/versions/20260718_0001_calendar_foundation.py`
- Backend: `backend/app/calendar/models.py`, `repository.py`, `service.py`,
  `schemas.py`, and `routes.py`
- Tests: `backend/tests/test_calendar_api.py`,
  `backend/tests/test_event_api.py`, and
  `backend/tests/test_read_only_database_guards.py`

If this milestone is reopened, keep its scope limited to regressions in these
acceptance criteria and update `instructions.md` plus `handoff.md` after
verification.
