# M10 — Notes and slide references

- [x] Milestone completed

## Outcome

Let the owner create course notes in a safe plain-text/Markdown format and
optionally connect each note to one or more explicit slide ranges.

## Data and validation

A note belongs to exactly one course and includes ID, course ID, title, body,
and timestamps. A note may have no slide connection.

Slide references use a separate relation with note ID, source ID, nullable
start/end slide, optional label, and timestamp. This supports several ranges
and whole-deck references without coupling the note to a single file.

The backend enforces that every linked source belongs to the same course and
has `source_type = slides`. Removing a link does not delete the note or source.
Deleting a source safely removes or invalidates its links. Rich document or
collaborative editing is outside this milestone.

## Completed checklist

- [x] Add Note and note-to-slide relation models and migration.
- [x] Add note CRUD services and routes.
- [x] Build the Notes tab and safe editor/display.
- [x] Allow notes without slide links.
- [x] Allow multiple slide decks and ranges per note.
- [x] Support whole-deck references with nullable ranges.
- [x] Validate same-course and Slides-library constraints server-side.
- [x] Show linked deck names and slide numbers clearly.
- [x] Handle link/source deletion safely.
- [x] Add backend and frontend tests.

## Acceptance criteria

- The owner can create, view, edit, and delete course notes.
- Notes work with no slides or with several explicit slide references.
- Invalid cross-course and literature links are rejected by the backend.
- Slide references remain visible and understandable in the note UI.
- Existing Course materials, Calendar, and Assistant behavior remains intact.

## Completion evidence and implementation areas

- Migration: `backend/alembic/versions/20260730_0012_course_notes.py`
- Backend: `backend/app/notes/`
- Frontend: `frontend/src/features/courses/CourseNotes.tsx` and
  `NoteDialog.tsx`
- Tests: `backend/tests/test_course_notes.py` and Courses frontend tests

AI summaries and arbitrary note modification through the Assistant are not
part of this milestone.
