# Courses module

## Ownership and current locations

Courses owns course records, sources and extraction/storage, Markdown notes and
slide links, summaries/bullet provenance, note prettify, course-calendar
association records, Courses UI/styles, and tests. Current backend locations are
`backend/app/{courses,course_sources,course_calendars,notes}/`; frontend code is
`frontend/src/features/courses/`. Tables are `courses`, `course_sources`,
`course_source_text`, `notes`, `note_source_links`, `note_summaries`, and
`course_calendar_links`. Migrations 0010-0014 and 0018 are Courses-owned content.

Uploaded Literature and Slides live beneath the configurable private course
storage root. Physical paths never cross a public contract.

## Required public contracts

These interfaces are specified but not yet implemented:

- An Assistant context port accepts explicit intent/query and strict size/count
  bounds; it returns typed course/note/slide excerpts with source IDs and
  provenance, never ORM entities or unrestricted source queries.
- A course-calendar association service owns list/link/unlink operations and
  consumes Calendar's public existence/event-query port. It returns bounded
  Calendar values and preserves Calendar records when a course/link is removed.
- `backend/app/courses/entry.py` and `frontend/src/features/courses/entry.ts`
  contribute the existing routes and page through Platform composition.
  Recovery and focused-test contributions remain pending.

Courses owns same-course source/link validation, source-type separation,
summary/prettify validation, and owner acceptance/save rules. Errors include
course/source/note not found, extraction state/content/storage errors,
same-course reference validation, stale summary/bullet conflicts, and Calendar
contract errors. Services own commits; filesystem create/delete operations keep
their existing rollback/quarantine compensation. Association changes use an
explicit coordinator rather than a shared Calendar repository/session.

## Dependencies and migration debt

Courses depends on Platform and Calendar's future public contract. Direct
Calendar models/repositories/services/schemas and UI imports are exact M21D
exceptions. Assistant context currently queries Courses ORM models directly;
M21E replaces that access. Direct AI/Codex paths and the Assistant-owned error
UI are M21F exceptions. Course feature CSS is global until M21E. Course storage
and archive logic remains coordinated with Platform recovery.

## Current commands

```bash
make dev
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/test_course_api.py tests/test_course_sources.py tests/test_course_notes.py tests/test_note_summaries.py tests/test_note_prettify.py tests/test_course_calendars.py
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/courses
make test
make e2e
make data-relocation-test
```

These selectors still use shared full-app fixtures. See the
[M21A baseline](../baseline.md).
