# M9 — Course materials and separated storage

- [x] Milestone completed

## Outcome

Add private course-source storage and a Materials UI that keeps literature and
slides distinct and extracts usable text from initial supported formats.

## Source and storage requirements

A source belongs to one course and includes its immutable ID, source type,
display/original/stored names, MIME type, size, internal storage path, optional
future external ID, extraction state/error, and timestamps.

The two source types are first-class values:

- `literature`
- `slides`

They remain separate in the database, API, storage layout, UI, and docs. Binary
files are stored beneath the configurable `COURSE_STORAGE_ROOT`, by immutable
course/source IDs, never in the relational database or Git. User filenames are
not trusted as paths.

## Extraction and safety

Prioritize PDF, PPTX, UTF-8 text, and Markdown. Preserve page/slide numbers when
possible and store extracted text separately with content hashes. Supported
files that yield no usable text do not count as successful. Failed extraction
is retryable; unsupported extraction does not prevent safe storage.

Uploads enforce size/type checks and path-traversal protection. Deletion may
remove only the selected source's data, and missing files must not corrupt
database state.

## Completed checklist

- [x] Add CourseSource and extracted-content models and migration.
- [x] Add distinct literature and slides types and directories.
- [x] Add configurable private course storage root.
- [x] Add safe upload and source deletion.
- [x] Build the Materials tab with separate libraries.
- [x] Show metadata, extraction status, errors, and retry controls.
- [x] Add extraction adapter for PDF, PPTX, TXT, and Markdown.
- [x] Avoid unnecessary re-extraction of unchanged content.
- [x] Document storage, backup, and deletion in `README.md`.
- [x] Add upload, storage, deletion, and extraction tests.

## Acceptance criteria

- Literature and slides are stored and displayed separately.
- The owner can identify and back up the course storage location.
- Unsupported extraction does not prevent safe file storage.
- Deleting one source cannot delete another source.
- Uploaded binaries and extracted private content are never committed.

## Completion evidence and implementation areas

- Migration: `backend/alembic/versions/20260730_0011_course_sources.py`
- Backend: `backend/app/course_sources/`
- Frontend: `frontend/src/features/courses/CourseMaterials.tsx`
- Tests: `backend/tests/test_course_sources.py`
- Owner documentation: course storage and backup sections in `README.md`

Automatic course downloads, OCR, and LMS synchronization are outside this
milestone.
