# Courses module

## Ownership and current locations

Courses owns course records, sources and extraction/storage, Markdown notes and
slide links, summaries/bullet provenance, note prettify, course-calendar
association records, safe application errors, UI, styles, and tests. Backend
code is in `backend/app/{courses,course_sources,course_calendars,notes}/`;
frontend code, including `styles.css`, is in `frontend/src/features/courses/`.
Tests are in `backend/tests/courses/`, colocated frontend tests, and
`e2e/tests/courses.spec.ts`. Tables are `courses`, `course_sources`,
`course_source_text`, `notes`, `note_source_links`, `note_summaries`, and
`course_calendar_links`. Migrations 0010-0014 and 0018 are Courses-owned content
in the centrally ordered Platform migration chain.

Uploaded Literature and Slides live beneath the configurable private course
storage root. Physical paths never cross a public contract.

## Implemented public contracts

`backend/app/courses/public.py` is the only Courses business surface consumed
by other backend features. It is read-only and exposes no ORM entity,
repository, session, or storage path:

- `list_courses` returns bounded `CourseSummary` identities for discovery.
- `find_notes` returns `NoteReference` identities, newest first, optionally
  limited to supplied course IDs and to notes containing supplied whole words.
  Bodies are read to match but never returned by this method.
- `get_note_context` returns `NoteExcerpt`, `SlideReference`, and `SlideExcerpt`
  values for explicitly supplied note IDs, truncated to the caller's character
  and count budgets. Only completed Slides sources inside a reference's slide
  range are included; Literature is never returned.
- `list_linked_calendar_ids` returns the Calendar IDs associated with supplied
  courses. Calendar remains the authority for what those calendars contain.

Every call is clamped to the hard limits declared in the module (for example
at most 8 context notes, 24,000 note characters, 40 slides, and 20,000 slide
characters); a request beyond a limit is rejected rather than truncated
silently. Returned values carry the course, note, and source IDs they came
from, so a consumer can validate citations against exactly what it received.

Assistant decides whether course context is relevant to a question and which
notes to ask for. That routing and selection policy is Assistant's and is not
part of this contract.

`backend/app/courses/entry.py` contributes the existing routers and re-exports
`courses_recovery_contribution`, the typed declaration of the established
`course_files` manifest key, `course-content.tar.gz` archive, `course_content`
root, and archive limits. Platform's coordinated archive helper consumes it;
quiescence, ordering, checksums, and rollback stay with Platform.
`frontend/src/features/courses/entry.ts` contributes the page and loads the
Courses stylesheet.

The course-calendar association service (`CourseCalendarService`) owns
list/link/unlink. It reads Calendar only through Calendar's public query port
and commits once: lock the course, have Calendar lock and revalidate the
calendar, change the link, commit. The port is read-only, so deleting a course
or a link removes the association and never a Calendar record.

Errors live in `app.courses.errors`: course/source/note/summary not found,
calendar not linked, extraction state, content, size and storage errors,
same-course slide-reference validation, stale summary and bullet conflicts, and
invalid summary or prettify responses. Codes, statuses, and messages are
unchanged from before they moved.

## Dependencies and remaining debt

Courses depends on Platform and on Calendar's public contracts. No Courses code
imports Calendar models, repositories, services, or schemas, and no other
feature imports Courses internals.

Embedded Calendar styling is an explicit contract. Courses targets or reuses
only the class names in `calendarEmbeddingClasses`, published by
`frontend/src/features/calendar/public.ts`.
`calendarStyleContract.test.ts` fails if Courses uses an unpublished Calendar
class or if Calendar stops providing a published one.

Feature stylesheets load before the shared Platform and global sheets. Where an
element carries both a shared class and a Courses class, the Courses selector
names both (for example `.primary-button.create-course-button`) so it wins by
specificity rather than by source order.

Summary and prettify consume Platform's shared AI runtime through
`app.platform.ai`; they do not load Assistant internals. Course-material errors
use the Platform-owned sanitized diagnostic contribution. `CoursesPage.tsx`
remains one orchestration component because splitting it was not needed to
isolate the module.

## Current commands

```bash
make dev
make dev-module MODULE=courses
make test-module MODULE=courses
make down-module MODULE=courses
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/courses
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/courses
make test
make e2e
make data-relocation-test
```

The Courses focused host closes dependencies to Platform, Calendar, and
Courses. It mounts their real routes and the Courses page, and includes
Calendar's ICS refresh lifecycle because Calendar is a required dependency.
Backend tests truncate only Courses and Calendar tables and give each test a
private course-storage root. The focused browser stack attaches an isolated
database and course storage only; summary and prettify requests are mocked.
`make test-module MODULE=courses` also runs the Assistant API tests and the
archive tests, because Assistant and Platform recovery consume Courses
contracts. See the [M21A baseline](../baseline.md).
