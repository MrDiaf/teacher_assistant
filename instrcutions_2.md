# Teacher Assistant

## Next Product Phase — Courses, Notes, Study Sources, and Course-Aware Assistant

---

# 1. Session Instruction

The Calendar and Assistant phases are already implemented and must remain working.

Before changing code:

1. Inspect the existing repository structure, database models, migrations, API conventions, frontend component patterns, tests, `AGENT.md`, and `README.md`.
2. Reuse the existing Teacher Assistant design system and Codex Python adapter.
3. Preserve all completed Calendar and Assistant functionality.
4. Do not rewrite working modules unless a small shared refactor is required.
5. Implement only the milestone explicitly selected for the current session.
6. Do not begin the next milestone automatically.
7. Do not mark an item complete unless the implementation and relevant tests pass.

For the current development session, implement only:

```text
M8 — Course foundation and manual course creation
```

The later milestones in this document define the intended architecture, but they are not permission to implement the whole phase at once.

At the end of the session, report:

- Files changed
- Database migrations added
- API routes added or changed
- Tests added
- Commands used to verify the work
- Any unfinished or blocked items
- The next recommended milestone

---

# 2. Product Goal

Add a Courses module inspired by the structure of a learning-management system such as Canvas, while preserving the existing Teacher Assistant visual identity.

The owner must initially be able to create and manage courses manually.

A course should provide one place for:

- Course information
- Course literature
- Lecture slides
- Notes
- AI-generated summaries
- Linked calendars
- Course-related assistant questions

Automatic course import is a future feature and is not part of this phase.

The architecture should allow a future LMS integration without forcing manually created courses to be redesigned.

---

# 3. Scope and Non-Goals

## Included in this product phase

- Manual course creation
- Course editing, archiving, and deletion
- Separate storage and metadata for course literature and slides
- Course notes
- Optional links between notes and slides
- AI summaries generated from notes and linked slides
- AI model selection
- Linking one or more existing calendars to a course
- Showing linked-calendar events inside the course
- Allowing the existing Assistant to access relevant course notes
- Safe, structured error explanations through the Assistant

## Not included yet

- Automatic Canvas import
- Canvas OAuth
- LTI integration
- University account login
- Automatic downloading of course material
- Automatic assignment submission
- Grade synchronization
- Multi-user courses
- Teacher or student roles
- Collaborative notes
- Autonomous source-code editing by the runtime Assistant
- Letting the browser call Codex directly
- Replacing the existing Calendar implementation

---

# 4. Visual Design

Preserve the existing Teacher Assistant shell shown in the current application:

- Fixed dark-green sidebar
- Warm off-white content background
- Dark-green primary text
- Gold accent
- Rounded cards and navigation highlights
- Existing typography and spacing
- Existing responsive behavior

The Courses navigation item should become functional.

Do not create a separate visual language that looks disconnected from Calendar and Assistant.

## Courses page

The Courses page should contain:

- Page heading: `Courses`
- Create course button
- Active courses section
- Archived courses section or filter
- Loading state
- Empty state
- Error state

Each course card should show, when available:

- Course name
- Course code
- Term
- Course color
- Short description
- Number of notes
- Number of uploaded sources
- Number of linked calendars

## Course detail page

Selecting a course should open a course detail page inside the existing application shell.

Use tabs or equivalent sections:

```text
Overview
Notes
Materials
Calendar
```

A future `Assignments` section may be added later, but it must not be implemented now.

---

# 5. Manual Course Management

A course should contain at least:

```text
id
name
course_code
description
term
color
status
created_at
updated_at
```

Initial status values:

```text
active
archived
```

The owner must be able to:

- Create a course manually
- Edit its name
- Edit its course code
- Edit its description
- Edit its term
- Change its color
- Archive it
- Restore an archived course
- Delete it after explicit confirmation

Course names do not have to be globally unique.

The UI must use the course ID internally and must not assume that the name is unique.

Deleting a course must never delete linked calendars or calendar events.

The exact deletion behavior for uploaded files must be explicit in the confirmation dialog.

---

# 6. Course Sources

A course supports two distinct source categories:

```text
literature
slides
```

They must remain distinct in the database, API, storage layout, UI, and documentation.

Do not represent them only as an arbitrary tag.

## Course literature

Examples:

- Textbooks
- Course compendiums
- Research papers
- Reading instructions
- Reference documents

## Slides

Examples:

- Lecture slide decks
- Seminar slides
- Presentation PDFs
- PowerPoint files

Slides are kept separate because notes and AI summaries may link directly to specific slide decks and slide numbers.

## Course source model

A source should contain at least:

```text
id
course_id
source_type
display_name
original_filename
stored_filename
mime_type
file_size
storage_path
external_id
extraction_status
extraction_error
created_at
updated_at
```

Initial `source_type` values:

```text
literature
slides
```

Initial `extraction_status` values:

```text
not_started
queued
processing
completed
failed
unsupported
```

`external_id` is nullable and reserved for future LMS imports.

Uploaded binary files must not be stored directly in the main relational database.

---

# 7. File Storage Layout

Use one configurable storage root.

Suggested environment variable:

```text
COURSE_STORAGE_ROOT
```

Suggested default for local development:

```text
./data/course_content
```

Store files by immutable course and source IDs rather than trusting user filenames.

Required logical layout:

```text
data/course_content/
└── <course-id>/
    ├── literature/
    │   └── <source-id>/
    │       └── original.<extension>
    └── slides/
        └── <source-id>/
            └── original.<extension>
```

The exact implementation may vary if the existing project already has a storage service, but literature and slides must have clearly separate directories.

The backend must:

- Sanitize uploaded filenames
- Reject path traversal
- Enforce a configurable maximum file size
- Validate file type using more than the filename extension when practical
- Never expose arbitrary server paths to the browser
- Delete only files belonging to the selected source or course
- Handle a missing file without corrupting database state

The `README.md` must document:

- The value and purpose of `COURSE_STORAGE_ROOT`
- The literature directory
- The slides directory
- How to back up course files
- How to remove course files safely
- What happens when a source or course is deleted
- Which data is stored in the database and which data is stored on disk

This documentation is required because the owner must be able to locate and remove course literature easily.

---

# 8. Notes

A note belongs to exactly one course.

A note may exist without any slide connection.

A note may optionally link to one or more slide references.

A note should contain at least:

```text
id
course_id
title
body
created_at
updated_at
```

Use Markdown or the project’s existing safe text format for the initial editor.

Do not add a complex collaborative editor during this phase.

## Note-to-slide links

Use a separate relation rather than putting one slide ID directly on the note.

A note-source link should contain at least:

```text
id
note_id
source_id
start_slide
end_slide
label
created_at
```

Rules:

- `source_id` must belong to the same course as the note.
- Only sources with `source_type = slides` may be linked as slide references.
- `start_slide` and `end_slide` are nullable when the note refers to the whole deck.
- A note can link to several slide ranges.
- Removing a link must not delete the note or slide file.
- Deleting a slide source must remove or invalidate its note links safely.

The note editor should show linked slide references clearly.

---

# 9. Text Extraction

AI summarization requires text, not only binary files.

Create an extraction service behind a stable adapter.

Initial supported formats should prioritize:

```text
PDF
PPTX
TXT
Markdown
```

Unsupported files may still be stored, but the UI must clearly state that AI text extraction is unavailable.

Extracted text should be stored separately from the binary file.

Suggested extracted content structure:

```text
id
source_id
page_or_slide_number
text
content_hash
created_at
updated_at
```

Requirements:

- Preserve page or slide numbers when possible.
- Never claim that extraction succeeded if no usable text was produced.
- Store a readable extraction error.
- Allow a failed extraction to be retried.
- Avoid re-extracting an unchanged file when the content hash matches.
- Do not send an entire large book or slide archive to Codex when only a small relevant portion is needed.

Course literature storage is part of this phase, but the first note-summary feature should summarize:

```text
note body + text from explicitly linked slide ranges
```

It should not automatically summarize all course literature.

---

# 10. AI Note Summaries

A note page should contain a button such as:

```text
Generate summary
```

Before generation, the owner should be able to select an allowed AI model.

The request flow must be:

```text
Owner selects a note and model
        ↓
React sends the note-summary request to FastAPI
        ↓
FastAPI loads the note and linked slide text
        ↓
FastAPI prepares a restricted Codex workspace
        ↓
FastAPI calls Codex through the existing Python adapter
        ↓
Codex returns structured summary bullets
        ↓
FastAPI validates the output
        ↓
Frontend displays the summary with source provenance
```

The browser must not:

- Import the Codex Python module
- Receive Codex credentials
- Send arbitrary model identifiers without backend validation
- Execute model output as code

## Summary output

Use structured output similar to:

```json
{
  "summary": [
    {
      "text": "The transport layer provides process-to-process communication.",
      "origin": "note",
      "source_references": [
        {
          "note_id": "note-1"
        }
      ]
    },
    {
      "text": "The lecture distinguishes flow control from congestion control.",
      "origin": "slide",
      "source_references": [
        {
          "source_id": "source-4",
          "slide": 18
        }
      ]
    },
    {
      "text": "Reliable delivery combines the mechanisms described in both sources.",
      "origin": "mixed",
      "source_references": [
        {
          "note_id": "note-1"
        },
        {
          "source_id": "source-4",
          "slide": 19
        }
      ]
    }
  ]
}
```

Allowed origins:

```text
note
slide
mixed
```

The backend must reject unknown origins and invalid source references.

## Visual distinction

Use slightly different visual styles:

- Note-derived bullet: green-tinted badge or border
- Slide-derived bullet: blue or purple-tinted badge or border
- Mixed bullet: gold-tinted badge or border

Do not rely only on color.

Each bullet must also display a text label or icon such as:

```text
From note
From slides
From note + slides
```

This is required for accessibility and to avoid misleading source attribution.

## Stored summaries

A generated summary should store at least:

```text
id
note_id
model
status
summary_json
note_content_hash
slide_content_hash
created_at
updated_at
```

The UI should indicate when a saved summary is stale because the note or linked slide text changed.

The owner should be able to regenerate it.

Do not store hidden model reasoning.

---

# 11. AI Model Selection

Add a shared backend-controlled model list.

Suggested route:

```text
GET /api/v1/ai/models
```

The route should return only models explicitly allowed by server configuration.

The owner should be able to select a model in:

- The main Assistant chat
- The note summarizer

The backend must:

- Validate the selected model against an allowlist
- Define a default model
- Return a clear error when a model is unavailable
- Never trust an arbitrary model string from the browser
- Store the selected model with each assistant message or summary job
- Keep model-specific SDK details inside the existing Codex adapter

The UI should remember the most recently selected model locally or through owner settings, following the project’s existing settings pattern.

Do not duplicate the model selector implementation in several unrelated components. Use a shared component where practical.

---

# 12. Course-Linked Calendars

A course may link to zero, one, or several existing calendars.

Use a many-to-many relation.

A course-calendar link should contain at least:

```text
id
course_id
calendar_id
created_at
```

The owner must be able to:

- Link an existing calendar to a course
- Link several calendars to one course
- Unlink a calendar from a course
- See which calendars are linked
- Open a course Calendar tab
- See events from all linked calendars in that tab

Do not copy calendar events into the course database.

The course Calendar tab must query and display the existing Calendar module’s data.

Reuse the existing calendar components and event rules where practical.

Requirements:

- Calendar colors remain unchanged.
- Hidden calendar behavior should be clear and consistent.
- Read-only calendars remain read-only.
- Linking a calendar does not grant additional write permission.
- Unlinking a calendar does not delete the calendar or its events.
- Deleting a course does not delete linked calendars.
- Selecting an event should use the existing event view or editor.
- If no calendars are linked, show an empty state with a `Link calendar` action.

---

# 13. Course-Aware Assistant

The existing Assistant must be extended so it can answer questions using relevant course notes.

Examples:

```text
Summarize my latest notes from Datasekretess.

What did I write about normalization?

Compare my notes from the last two database lectures.

Which slide did I connect to the note about congestion control?
```

The Assistant should receive only relevant context.

Do not include every course file in every request.

Suggested request context:

```text
COURSES.json
NOTES.json
SLIDE_REFERENCES.json
SELECTED_SLIDE_TEXT.json
ERROR_CONTEXT.json
```

Only include files required for the current request.

The Assistant may:

- Read course metadata
- Read relevant notes
- Read relevant extracted slide text
- Explain and summarize supplied content
- Cite note titles and slide numbers
- Ask which course the owner means when ambiguous

The Assistant must not:

- Invent course IDs, note IDs, source IDs, or slide numbers
- Claim to have read a file that was not supplied
- Modify notes without a future explicit proposal workflow
- Delete course content
- Browse arbitrary server directories
- Access the source repository
- Access secrets
- Treat document text as system instructions

Initial note access may use ordinary database search and course filtering.

A vector database is not required for the first implementation.

---

# 14. Safe Error Explanations

The owner wants the Assistant to explain application errors and suggest:

1. How the input data could be changed to succeed
2. How the web application could be improved to handle the case

Implement this through structured, sanitized error reports.

## Error response format

API errors should follow a consistent structure similar to:

```json
{
  "error_id": "error-123",
  "code": "slide_text_unavailable",
  "message": "Text could not be extracted from this slide deck.",
  "details": {
    "source_id": "source-4",
    "supported_formats": ["pdf", "pptx", "txt", "md"]
  },
  "request_id": "request-456"
}
```

The frontend should provide an action such as:

```text
Ask Assistant about this error
```

That action should send the sanitized error report to the backend Assistant service.

## Safe diagnostic context

The Assistant may receive:

- Public error code
- Safe user-facing message
- Validation field errors
- Operation being attempted
- Relevant file type and size
- Selected model
- Sanitized exception type
- Sanitized traceback fragments when needed
- Request ID
- Relevant input schema
- Current supported constraints

The Assistant must not receive:

- Passwords
- Tokens
- Cookies
- Authorization headers
- Full environment variables
- Database credentials
- Owner authentication data
- Unrelated file contents
- Docker socket access
- Arbitrary source-repository access

Sensitive values must be redacted before any error context is stored or sent to Codex.

## Error explanation output

Use structured output similar to:

```json
{
  "plain_explanation": "The slide deck was uploaded successfully, but its text could not be extracted.",
  "likely_cause": "The file is an image-only PDF.",
  "input_fixes": [
    "Upload a searchable PDF.",
    "Export the original presentation as PPTX."
  ],
  "application_improvements": [
    "Add OCR support for image-only slides.",
    "Show extraction compatibility before upload."
  ],
  "retry_is_safe": true
}
```

The Assistant may suggest an application improvement, but the runtime Assistant must not edit the source code or claim that the improvement was implemented.

Exact code repair belongs to a separate development workflow, not the daily user-facing Assistant.

---

# 15. Backend Structure

Follow the current project architecture.

Suggested additions:

```text
backend/app/
├── courses/
│   ├── routes.py
│   ├── service.py
│   ├── repository.py
│   ├── schemas.py
│   └── models.py
├── course_sources/
│   ├── routes.py
│   ├── service.py
│   ├── storage.py
│   ├── extraction.py
│   └── schemas.py
├── notes/
│   ├── routes.py
│   ├── service.py
│   ├── repository.py
│   ├── schemas.py
│   └── models.py
├── summaries/
│   ├── routes.py
│   ├── service.py
│   ├── schemas.py
│   └── validation.py
└── diagnostics/
    ├── service.py
    ├── schemas.py
    ├── redaction.py
    └── models.py
```

This is a suggestion, not a requirement to duplicate layers that already exist.

Prefer consistency with the repository over creating unnecessary folders.

Reuse the existing:

- Database session
- Migration system
- API error conventions
- Authentication assumptions
- Codex adapter
- Runtime workspace builder
- Job status handling
- Frontend component library
- Test fixtures

---

# 16. Suggested API Routes

Use the existing versioned API prefix.

## Courses

```text
GET    /api/v1/courses
POST   /api/v1/courses
GET    /api/v1/courses/{course_id}
PATCH  /api/v1/courses/{course_id}
DELETE /api/v1/courses/{course_id}
POST   /api/v1/courses/{course_id}/archive
POST   /api/v1/courses/{course_id}/restore
```

## Sources

```text
GET    /api/v1/courses/{course_id}/sources
POST   /api/v1/courses/{course_id}/sources
GET    /api/v1/course-sources/{source_id}
DELETE /api/v1/course-sources/{source_id}
POST   /api/v1/course-sources/{source_id}/extract
POST   /api/v1/course-sources/{source_id}/retry-extraction
```

## Notes

```text
GET    /api/v1/courses/{course_id}/notes
POST   /api/v1/courses/{course_id}/notes
GET    /api/v1/notes/{note_id}
PATCH  /api/v1/notes/{note_id}
DELETE /api/v1/notes/{note_id}
POST   /api/v1/notes/{note_id}/slide-links
DELETE /api/v1/notes/{note_id}/slide-links/{link_id}
```

## Summaries and models

```text
GET  /api/v1/ai/models
POST /api/v1/notes/{note_id}/summaries
GET  /api/v1/summary-jobs/{job_id}
GET  /api/v1/notes/{note_id}/summaries
```

## Course calendars

```text
GET    /api/v1/courses/{course_id}/calendars
POST   /api/v1/courses/{course_id}/calendars
DELETE /api/v1/courses/{course_id}/calendars/{calendar_id}
GET    /api/v1/courses/{course_id}/events
```

## Diagnostics

```text
GET  /api/v1/diagnostics/errors/{error_id}
POST /api/v1/assistant/errors/{error_id}/explain
```

Exact route names may change if the architecture remains clear and consistent.

---

# 17. Future Automatic Course Import

Do not implement automatic import during this phase.

Prepare for it by keeping manual and imported courses distinguishable.

A future course may contain:

```text
source_type
external_system
external_course_id
sync_status
last_synced_at
```

Possible future `source_type` values:

```text
manual
lms_import
```

Future LMS synchronization should use a dedicated adapter interface.

Examples may include an official Canvas API or another university LMS API.

Do not build the current course model around HTML scraping.

Manually created courses must continue to work even if an LMS integration is unavailable.

Imported material should preserve external IDs and should not silently overwrite local notes.

---

# 18. Development Milestones

Implement one milestone at a time.

## M8 — Course foundation and manual course creation

- [ ] Inspect and preserve the existing application shell.
- [ ] Add the Course database model.
- [ ] Add migrations.
- [ ] Add course CRUD schemas, service, repository, and API routes.
- [ ] Add archive and restore behavior.
- [ ] Build the Courses page.
- [ ] Add create-course form.
- [ ] Add edit-course form.
- [ ] Add course cards and empty states.
- [ ] Add the basic Course detail page with placeholder tabs.
- [ ] Add backend tests.
- [ ] Add frontend tests where practical.
- [ ] Update milestone documentation.

Acceptance:

- The owner can create, view, edit, archive, restore, and delete a manual course.
- The Courses page matches the existing Teacher Assistant design.
- Calendar and Assistant still work.
- Materials, notes, summaries, and calendar linking are not implemented yet.
- Tests pass.

---

## M9 — Course materials and separated storage

- [ ] Add CourseSource model.
- [ ] Add `literature` and `slides` source types.
- [ ] Add configurable course storage root.
- [ ] Add safe upload and deletion.
- [ ] Add Materials tab.
- [ ] Visually separate literature from slides.
- [ ] Add source metadata and file status.
- [ ] Add text extraction adapter.
- [ ] Support initial PDF, PPTX, TXT, and Markdown extraction.
- [ ] Add extraction status and retry.
- [ ] Document exact storage directories in `README.md`.
- [ ] Add storage, upload, deletion, and extraction tests.

Acceptance:

- Literature and slides are stored and displayed separately.
- The owner can easily identify where course literature is stored.
- Unsupported extraction does not prevent safe file storage.
- Deleting one source cannot delete another source.

---

## M10 — Notes and slide references

- [ ] Add Note model.
- [ ] Add note CRUD.
- [ ] Add Notes tab.
- [ ] Add safe Markdown or plain-text editor.
- [ ] Add note-to-slide relation.
- [ ] Allow a note with no slides.
- [ ] Allow one or more linked slide ranges.
- [ ] Validate that linked slides belong to the same course.
- [ ] Show linked deck names and slide numbers.
- [ ] Add tests.

Acceptance:

- The owner can create course notes.
- Notes work with or without linked slides.
- Slide references are preserved and visible.

---

## M11 — AI summaries and model selection

- [ ] Add backend model allowlist and default model.
- [ ] Add shared model-selection endpoint.
- [ ] Add model selector to Assistant.
- [ ] Add model selector to note summaries.
- [ ] Extend the existing Codex adapter rather than creating a second integration.
- [ ] Build restricted summary workspaces.
- [ ] Add structured summary output.
- [ ] Add `note`, `slide`, and `mixed` provenance.
- [ ] Add accessible visual distinction.
- [ ] Store summary model and source hashes.
- [ ] Mark stale summaries.
- [ ] Add retries and safe errors.
- [ ] Mock Codex in automated tests.

Acceptance:

- The owner can choose an allowed model.
- A note can be summarized from its body and linked slide text.
- Every bullet clearly states where it came from.
- The browser never contacts Codex directly.

---

## M12 — Course-linked calendars

- [ ] Add course-calendar relation.
- [ ] Add link and unlink API routes.
- [ ] Add calendar selection UI.
- [ ] Add Course Calendar tab.
- [ ] Reuse existing calendar components.
- [ ] Filter the view to linked calendars.
- [ ] Preserve read-only restrictions.
- [ ] Preserve existing event behavior.
- [ ] Add tests.

Acceptance:

- One course may link to several calendars.
- Entering the course Calendar tab shows events from linked calendars.
- Events are not duplicated.
- Unlinking or deleting a course does not delete calendar data.

---

## M13 — Course-aware Assistant and diagnostics

- [ ] Extend Assistant context with relevant course notes.
- [ ] Add course-aware clarification behavior.
- [ ] Add note and slide citations.
- [ ] Add structured safe error reports.
- [ ] Add redaction.
- [ ] Add `Ask Assistant about this error`.
- [ ] Add input-fix and application-improvement output.
- [ ] Prevent runtime source-code editing.
- [ ] Add audit records.
- [ ] Add privacy and safety tests.
- [ ] Add end-to-end tests.
- [ ] Update setup, backup, restore, and troubleshooting documentation.

Acceptance:

- The Assistant can answer questions using relevant course notes.
- The Assistant can explain a sanitized error.
- The explanation separates input changes from possible application improvements.
- Secrets and unrelated private data are never included.
- Existing Calendar and Assistant safety rules remain enforced.

---

# 19. Current Implementation Command

For this session:

```text
Implement M8 only.
```

Do not implement M9, M10, M11, M12, or M13.

However, keep the M8 model and routes compatible with the future milestones described above.

When M8 is complete, stop and provide a review before beginning M9.
