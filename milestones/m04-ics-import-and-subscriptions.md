# M4 — ICS import and subscriptions

- [x] Milestone completed

## Outcome

Allow the owner to safely preview and import `.ics` calendar data and subscribe
to an ICS feed that refreshes daily.

## Dependencies and safety

- M1–M3 remain functional.
- Imported and subscribed calendars default to read-only.
- Preserve external UIDs when present and use them to avoid obvious duplicate
  imports.
- Malformed or unsupported content must produce a readable error without
  partially corrupting calendar data.
- A subscription refresh is a controlled import path; it does not weaken
  read-only protections for owner or Assistant mutations.

## Completed checklist

- [x] Add `.ics` upload and preview.
- [x] Allow selection or creation of an import destination.
- [x] Preserve external event UIDs.
- [x] Prevent obvious duplicate imports.
- [x] Default imported calendars to read-only.
- [x] Report malformed or unsupported entries clearly.
- [x] Add ICS URL subscriptions with daily refresh behavior.
- [x] Guard import finalization and subscription updates.
- [x] Add import and subscription tests.

## Acceptance criteria

- The owner can preview and import an ICS calendar safely.
- Re-importing events with stable UIDs does not create obvious duplicates.
- Imported/subscribed events are visible but protected from ordinary mutation.
- Subscription failures do not erase a previously valid calendar.
- Relevant parser, import, subscription, and read-only tests pass.

## Completion evidence and implementation areas

- Migrations:
  - `backend/alembic/versions/20260719_0003_ics_import.py`
  - `backend/alembic/versions/20260719_0004_import_finalization_guard.py`
  - `backend/alembic/versions/20260719_0005_ics_subscriptions.py`
- Backend: `backend/app/calendar/ics.py`, `ics_fetch.py`, import routes/service,
  and subscription routes/service/scheduler
- Frontend: `frontend/src/features/calendar/IcsImportDialog.tsx`
- Tests: `backend/tests/test_ics_import.py` and
  `backend/tests/test_ics_subscriptions.py`

Live Google Calendar synchronization and OAuth are outside this milestone.
