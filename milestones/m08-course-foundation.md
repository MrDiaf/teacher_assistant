# M8 — Course foundation and manual course creation

- [x] This milestone

## Outcome

Make the Courses navigation item functional and add manual single-owner course
management while preserving the completed Calendar and Assistant modules.

## Course model and behavior

A course includes at least ID, name, course code, description, term, color,
status, and timestamps. Initial statuses are `active` and `archived`. Names need
not be unique; the UI and API use immutable IDs.

The owner can create, view, edit, archive, restore, and explicitly confirm
deletion of a manual course. Deleting a course never deletes linked calendars
or calendar events. File-deletion behavior must be explicit once sources exist.

## UI and boundaries

The Courses page follows the existing visual system and provides active and
archived views, cards, counts where available, create/edit forms, and loading,
empty, and error states. Course details provide Overview, Notes, Materials, and
Calendar tabs; later tabs may initially be placeholders.

Do not implement materials, notes, AI summaries, course-calendar linking,
automatic LMS import, assignments, grades, or multi-user course roles here.

## Completed checklist

- [x] Inspect and preserve the application shell and completed modules.
- [x] Add the Course model and migration.
- [x] Add course schemas, repository, service, and versioned API routes.
- [x] Add archive and restore behavior.
- [x] Build the Courses page and course cards.
- [x] Add create and edit forms.
- [x] Add loading, empty, and error states.
- [x] Add basic Course detail tabs.
- [x] Add backend and practical frontend tests.

## Acceptance criteria

- The owner can create, view, edit, archive, restore, and delete a manual
  course.
- Courses use IDs rather than assuming unique names.
- The Courses UI matches Teacher Assistant.
- Calendar and Assistant behavior remains intact.
- Materials, notes, summaries, and calendar linking are not required.

## Completion evidence and implementation areas

- Migration: `backend/alembic/versions/20260730_0010_course_foundation.py`
- Backend: `backend/app/courses/`
- Frontend: `frontend/src/features/courses/CoursesPage.tsx`,
  `CourseDialog.tsx`, and `DeleteCourseDialog.tsx`
- Tests: `backend/tests/test_course_api.py` and Courses frontend tests

Automatic Canvas/LMS import remains future scope and must receive its own
owner-defined milestone.
