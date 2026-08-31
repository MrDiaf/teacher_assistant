# M12 — Course-linked calendars

- [x] Milestone completed

## Outcome

Link courses to existing calendars without copying events, then reuse the main
Calendar experience inside a course-scoped Calendar tab.

## Relation and ownership rules

A course may link to zero, one, or several existing calendars through a
many-to-many relation. Linking grants no ownership or new write permission.
Unlinking and course deletion never delete calendars or events.

The course Calendar tab queries existing calendar/event data and reuses the
main calendar's views, toolbar, dialogs, recurrence behavior, drag/move/resize
logic, and visibility state where practical. Calendar colors remain unchanged.
If none are linked, show an empty state with a Link calendar action.

## Read-only safety

Linked read-only calendars remain visible, searchable, and usable for
availability. Mutation controls are disabled in the course UI, and backend
calendar services reject direct API attempts. Linking a calendar can never turn
off read-only protection.

## Completed checklist

- [x] Add course-calendar relation and migration.
- [x] Add link, list, unlink, and course-event routes.
- [x] Add calendar selection/linking UI.
- [x] Build the Course Calendar tab.
- [x] Reuse existing calendar components and behavior.
- [x] Scope the view to linked calendars.
- [x] Preserve calendar colors and visibility behavior.
- [x] Preserve read-only restrictions in UI and backend.
- [x] Prevent unlink/course deletion from deleting calendar data.
- [x] Add backend and frontend tests.

## Acceptance criteria

- A course can link to several calendars and display all linked events.
- Events are referenced, not duplicated.
- Existing event view/edit and recurrence behavior remains consistent.
- Read-only linked calendars cannot be mutated.
- Unlinking a calendar or deleting a course leaves calendars/events intact.

## Completion evidence and implementation areas

- Migration: `backend/alembic/versions/20260730_0014_course_calendars.py`
- Backend: `backend/app/course_calendars/`
- Frontend: `frontend/src/features/courses/CourseCalendar.tsx`
- Tests: `backend/tests/test_course_calendars.py` and
  `frontend/src/features/courses/CourseCalendar.test.tsx`

This milestone does not authorize copying events into course-specific storage
or weakening global calendar permission rules.
