# Calendar module

## Ownership and current locations

Calendar owns calendars/events, recurrence and exception semantics, ICS parsing,
import/subscription fetching and scheduling, read-only rules, API routes, safe
application errors, UI, styles, and Calendar tests. Current code is in
`backend/app/calendar/`, `frontend/src/features/calendar/`,
`backend/tests/calendar/`, colocated frontend tests, and
`e2e/tests/calendar.spec.ts`. Tables are `calendars`
and `events`; migrations 0001-0005 are Calendar-owned content in the centrally
ordered Platform migration chain.

Calendar currently has no filesystem or credential root. Imported and
subscribed calendar configuration is private PostgreSQL data.

## Implemented public contracts

`backend/app/calendar/public.py` is the only Calendar business surface consumed
by other backend features:

- A query port accepts explicit calendar/event IDs, bounded ranges, search, and
  availability inputs and returns typed `CalendarSummary`/`EventSummary` values.
- Courses binds the read-only query port for existence checks and bounded event
  lists for supplied linked IDs. Courses still owns association records.
- An Assistant command port exposes only create/update calendar and
  create/update/delete individual event operations already allowed by proposal
  policy. It has no calendar deletion, protection change, raw repository, bulk
  delete, or session escape hatch.
- `backend/app/calendar/entry.py` and `frontend/src/features/calendar/entry.ts`
  contribute the existing routers, page, stylesheet, and ICS refresh lifecycle.
- `frontend/src/features/calendar/public.ts` exports only the Calendar workspace,
  bounded display types/sidebar contract, and read-only list operation needed
  by Courses. It does not export mutation APIs or Calendar internals.
- The same file publishes `calendarEmbeddingClasses`: the class names an
  embedding feature may target or reuse. Calendar must keep styling or
  rendering each one. A contract test in Courses enforces both directions.

Errors live in `app.calendar.errors` and remain explicit safe application
errors: not found, read-only/source protected, invalid time/recurrence,
database protection, and invalid ICS or subscription input. Calendar remains
the final permission authority. Manual service operations own their commits.
The Assistant port is bound by the proposal coordinator, flushes Calendar
changes without committing, and preserves one transaction across Assistant and
Calendar state without exposing a session through the public API.

## Dependencies and migration debt

Calendar depends only on Platform configuration/errors/database infrastructure.
Courses and Assistant consume the exact `app.calendar.public` contract;
Courses consumes the exact `features/calendar/public` frontend contract. No
M21D exception remains in the boundary manifest. The generic `enum_values`
helper lives in Platform database infrastructure. Calendar selectors live in
`features/calendar/styles.css`. Courses' embedded `.course-calendar .calendar-*`
overrides are limited to the published `calendarEmbeddingClasses`.

## Current commands

```bash
make dev
make dev-module MODULE=calendar
make test-module MODULE=calendar
make down-module MODULE=calendar
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/calendar
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/calendar
make test
make e2e
```

The Calendar focused host closes dependencies to Platform plus Calendar,
includes the real routes/page and ICS lifecycle, and uses an isolated database.
Focused unit and browser Compose mount no private owner storage and the browser
spec seeds every test independently. See the [M21A baseline](../baseline.md).
