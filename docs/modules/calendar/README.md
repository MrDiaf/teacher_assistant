# Calendar module

## Ownership and current locations

Calendar owns calendars/events, recurrence and exception semantics, ICS parsing,
import/subscription fetching and scheduling, read-only rules, API routes, UI,
styles, and Calendar tests. Current code is in `backend/app/calendar/`,
`frontend/src/features/calendar/`, Calendar backend tests, Calendar frontend
tests, and Calendar portions of the combined E2E file. Tables are `calendars`
and `events`; migrations 0001-0005 are Calendar-owned content in the centrally
ordered Platform migration chain.

Calendar currently has no filesystem or credential root. Imported and
subscribed calendar configuration is private PostgreSQL data.

## Required public contracts

These are required interfaces, not yet implemented public entry points:

- A query port accepts explicit calendar/event IDs, bounded ranges, search, and
  availability inputs and returns typed `CalendarSummary`/`EventSummary` values.
- A Courses port verifies calendar existence and returns bounded events for a
  supplied set of linked IDs. Courses owns the association records.
- An Assistant command port exposes only create/update calendar and
  create/update/delete individual event operations already allowed by proposal
  policy. It has no calendar deletion, protection change, raw repository, bulk
  delete, or session escape hatch.
- A module entry contributes routers, page metadata, lifecycle hook, and later
  focused-test registration to Platform composition.

Errors remain explicit safe application errors: not found, read-only/source
protected, invalid time/recurrence, database protection, and invalid ICS or
subscription input. Calendar remains the final permission authority. Manual
service operations own their commits. Atomic Assistant proposal execution is
owned by the application coordinator described in the module index and must
preserve one commit across Assistant and Calendar state.

## Dependencies and migration debt

Calendar depends only on Platform configuration/errors/database infrastructure.
Courses and Assistant currently import Calendar ORM entities, repositories,
schemas, services, UI types/components, and API utilities directly. Exact paths
are in the boundary manifest and are removed in M21D. The generic `enum_values`
helper currently under Calendar models is imported by other owners and moves to
Platform in M21B. `main.py` router/scheduler imports move behind public entries
in M21B. Calendar selectors remain in global `styles.css` until M21D.

## Current commands

```bash
make dev
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/test_calendar_api.py tests/test_event_api.py tests/test_ics_import.py tests/test_ics_subscriptions.py tests/test_read_only_database_guards.py
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/calendar
make test
make e2e
```

The direct commands select Calendar files but do not yet provide the isolated
module host planned for M21C/M21D. See the [M21A baseline](../baseline.md).
