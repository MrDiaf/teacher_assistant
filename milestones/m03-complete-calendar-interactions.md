# M3 — Complete calendar interactions

- [x] Milestone completed

## Outcome

Complete normal personal-calendar interactions: moving, resizing, all-day and
recurring events, searching, filtering, and calendar management.

## Dependencies and safety

- M1 and M2 remain functional.
- Backend services remain authoritative for read-only protection.
- The frontend must disable or hide every mutation path for read-only
  calendars, including forms, drag/drop, resize, occurrence editing, and
  changing an event's calendar.
- Manual owner controls may execute after normal form confirmation; this does
  not authorize Codex-generated changes.

## Completed checklist

- [x] Add drag-and-drop event movement.
- [x] Add event resizing.
- [x] Add all-day events and all-day display areas.
- [x] Add recurring events and recurrence exceptions.
- [x] Add occurrence-versus-series editing.
- [x] Add search across title, description, and location.
- [x] Add calendar and date-range filters.
- [x] Add manual calendar create/edit/visibility/read-only/delete controls.
- [x] Add clear read-only visual states.
- [x] Prevent every frontend mutation against read-only calendars.
- [x] Add recurrence, interaction, and backend permission tests.

## Acceptance criteria

- Calendar interactions behave like a normal personal calendar in day, week,
  and month views.
- Recurring edits clearly distinguish one occurrence from the series.
- Search and filters return the intended events.
- Read-only calendars remain visible, searchable, and useful for availability
  while all mutation attempts fail.
- Calendar deletion is a manual owner action with confirmation.

## Completion evidence and implementation areas

- Migration: `backend/alembic/versions/20260719_0002_recurrence_exceptions.py`
- Backend: calendar models, schemas, repository, and service under
  `backend/app/calendar/`
- Frontend: calendar views, dialogs, filters, recurrence utilities, and API
  under `frontend/src/features/calendar/`
- Tests: event API, read-only database guards, calendar page, recurrence, and
  date utility tests

If reopened, verify both frontend prevention and backend rejection; a UI-only
read-only fix does not satisfy this milestone.
