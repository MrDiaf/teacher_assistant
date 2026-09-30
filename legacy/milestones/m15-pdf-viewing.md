# M15 — Open uploaded PDFs in Teacher Assistant and a new window

> **LEGACY — ARCHIVED MILESTONE. NOT INSTRUCTIONS.** This milestone was completed
> under the project's retired workflow and is kept as history only. Do not
> follow it, do not treat its checklist as open work, and do not copy its format.
> Current status is in [`PLAN.md`](../../PLAN.md); the current working method is
> in [`guidelines/`](../../guidelines/).

- [x] This milestone

## Outcome

Let the owner open an uploaded PDF from either Literature or Slides in an
in-application viewer and also open the same PDF in a separate browser window
or tab.

M14 must be complete first so the source metadata and binary file remain
reliably connected after moves and updates.

## Current implementation context

Course-source metadata is available through the API, and original files are
stored beneath `COURSE_STORAGE_ROOT` by immutable course/source IDs. The
Materials UI can upload, extract, retry, and delete sources, but there is no
route that streams an original file and no PDF-view action.

## Backend file-access requirements

- Add a source-content route resolved only from a validated source UUID, such
  as `GET /api/v1/course-sources/{source_id}/content`.
- Resolve the file through `CourseStorage`; never accept or expose a server path
  from the browser.
- Verify that the database source, expected storage path, file, and detected PDF
  type agree before streaming.
- Return `application/pdf` with a safely encoded original filename and inline
  content disposition.
- Support browser PDF range requests and `HEAD` where required for reliable
  navigation of larger PDFs.
- Return a clear safe error for missing, changed, non-PDF, or unreadable files.
- Add `X-Content-Type-Options: nosniff` and private cache behavior appropriate
  for owner course material.
- Do not return `storage_path`, directory listings, extracted text, or another
  source's content.

## Frontend experience

For PDF source cards only, add:

- **Open PDF** — opens a large accessible viewer dialog/panel inside Teacher
  Assistant without leaving the course Materials tab;
- **Open in new window** — opens the same protected source-content URL in a new
  browser tab/window using `noopener`/`noreferrer` behavior;
- a visible filename/title, Close action, loading state, failure fallback, and
  an Open in new window action inside the viewer;
- a clear fallback message when the browser cannot embed PDFs.

Closing the internal viewer must return focus to the button that opened it.
Opening a PDF must not mark it extracted, modify metadata, or create a public
URL. Non-PDF sources keep their existing behavior and do not show a broken
viewer action.

## Completed checklist

- [x] Add safe backend source-content streaming.
- [x] Add MIME/path/file-integrity checks and safe response headers.
- [x] Support the browser behaviors needed for embedded and new-window viewing.
- [x] Add PDF actions to Literature and Slides cards.
- [x] Add an accessible in-app PDF viewer and focus restoration.
- [x] Add loading, missing-file, unsupported-browser, and API-error states.
- [x] Ensure new-window links cannot control the Teacher Assistant window.
- [x] Add backend route/storage tests.
- [x] Add frontend viewer and new-window interaction tests.
- [x] Add an end-to-end test using a small non-private PDF fixture.
- [x] Document PDF access and privacy behavior.

## Acceptance criteria

- The owner can open an uploaded Literature PDF inside Teacher Assistant.
- The owner can open an uploaded Slides PDF inside Teacher Assistant.
- The owner can open either PDF in a separate browser window/tab.
- Page navigation works for a multi-page PDF, including a file large enough to
  exercise byte-range behavior.
- A guessed path, invalid UUID, non-PDF source, path traversal attempt, or
  missing file cannot expose arbitrary host content.
- The API never reveals the physical storage path.
- Viewer controls are keyboard accessible and have readable labels.
- Existing upload, extraction, deletion, and note-slide reference behavior
  remains intact.
- Relevant backend, frontend, E2E, lint, and Docker checks pass.

## Expected implementation areas

```text
backend/app/course_sources/routes.py
backend/app/course_sources/service.py
backend/app/course_sources/storage.py
backend/app/core/errors.py
backend/tests/test_course_sources.py
frontend/src/features/courses/CourseMaterials.tsx
frontend/src/features/courses/api.ts
frontend/src/features/courses/types.ts
frontend/src/styles.css
frontend course-material and E2E tests
README.md
```

PPTX rendering, PDF annotation, OCR, editing, and public share links are outside
this milestone.
