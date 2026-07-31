# Teacher Assistant development handoff

Updated: 2026-07-31
Repository: `/home/ronny/Public/projects/teacher_assitant`

## Start here

1. Read `AGENTS.md` completely and follow its session-canary instruction.
2. Read `instrcutions_2.md` (the filename is intentionally misspelled).
3. Run `git status --short` before changing anything and preserve owner work.
4. Inspect the implementation before deciding that functionality is missing.
5. M8 through M13 are complete. Do not begin a new milestone or future product
   phase without an explicit owner request.
6. Do not commit, push, merge, rebase, delete branches, or discard work unless
   the owner explicitly asks.

The old “Implement M8 only” text near the bottom of `instrcutions_2.md` was
superseded by the owner's later milestone requests and the completed M8–M13
checklists.

## Current state

- Git `HEAD`: `0e1fa6f M13 is done`
- M8 through M13 are committed and complete.
- No M14 is currently defined or in progress.
- Docker development services are running:
  - Frontend: `http://localhost:5173`
  - Backend: `http://localhost:8000`
  - PostgreSQL: healthy
- Alembic is at `20260730_0015 (head)`.
- `.openai/hosting.json` is absent. This remains a self-hosted Docker
  application; do not deploy it through Sites.
- At the time this handoff was recreated, `handoff.md` was the only worktree
  change (it had been deleted and was restored by this document).

Recheck the state at the start of the next session:

```bash
git status --short
docker compose -f compose.yml -f compose.dev.yml ps
docker compose -f compose.yml -f compose.dev.yml exec -T backend alembic current
```

## Non-negotiable product and safety constraints

- This is a single-owner application. Do not add registration, accounts,
  organizations, teams, roles, tenants, or shared profiles.
- Preserve the fixed dark-green sidebar, warm off-white background, gold
  accent, module-based shell, and existing Calendar/Assistant behavior.
- Keep development Docker-first and preserve the root Makefile commands.
- The browser must never communicate with Codex directly.
- Runtime Codex must never receive the repository, Docker socket, shell,
  environment files, database credentials, OAuth credentials, or unrelated
  private data.
- Codex output is untrusted. Codex must never update the database directly;
  backend services parse, validate, confirm, and execute allowed actions.
- Every Codex-generated calendar mutation requires owner confirmation.
- Read-only calendar protection must remain enforced in the UI, backend
  service, and database-changing operations. The backend is authoritative.
- Do not add a Codex delete-calendar action, bulk deletion, or any workaround
  for read-only calendars.
- Do not implement course import, study-plan functionality, document systems,
  or other future modules unless the owner explicitly starts that phase.

## Completed milestones

### M8 — Course foundation

- Manual course CRUD, archive/restore, deletion, course cards, and course
  detail shell.
- Backend: `backend/app/courses/`
- Frontend: `frontend/src/features/courses/`

### M9 — Course materials

- Separate Literature and Slides libraries.
- Private storage under `data/course_content`.
- PDF, PPTX, UTF-8 text, and Markdown extraction.
- Extraction states, retry behavior, and safe source deletion.
- Migration: `backend/alembic/versions/20260730_0011_course_sources.py`

### M10 — Notes and slide references

- Note CRUD with safe plain-text/Markdown display.
- Notes can link zero or several explicit slide ranges.
- Same-course and Slides-library validation is server-side.
- Backend: `backend/app/notes/`
- Frontend: `frontend/src/features/courses/CourseNotes.tsx`
- Migration: `backend/alembic/versions/20260730_0012_course_notes.py`

### M11 — AI summaries and model selection

- Server-authoritative model registry at `GET /api/v1/ai/models`.
- Shared Assistant/summary model selector with backend allowlist validation.
- Default model is `gpt-5.6-sol`; configured model IDs come from
  `AI_ALLOWED_MODELS`.
- Assistant jobs persist the selected model, and retries revalidate it.
- Note summaries persist model, status, strict structured output, content
  hashes, safe errors, and timestamps.
- Summary workspaces contain only the requested note, explicitly linked slide
  text, runtime policy, and output schema.
- Provenance is validated as `note`, `slide`, or `mixed`; invented or
  mismatched references fail safely.
- Summaries become stale when note text, linked ranges, or linked extracted
  slide text changes.
- Migration: `backend/alembic/versions/20260730_0013_ai_summaries.py`

### M12 — Course-linked calendars

- Courses link to existing calendars through a many-to-many association.
- Linking or unlinking never deletes calendars or events.
- Routes:
  - `GET /api/v1/courses/{course_id}/calendars`
  - `POST /api/v1/courses/{course_id}/calendars`
  - `DELETE /api/v1/courses/{course_id}/calendars/{calendar_id}`
  - `GET /api/v1/courses/{course_id}/events`
- The Course Calendar tab reuses the main calendar's views, toolbar, event
  dialog, recurrence handling, drag/move/resize behavior, and visibility state.
- Linked read-only calendars remain visible while all mutation controls and
  server-side operations remain protected.
- Migration: `backend/alembic/versions/20260730_0014_course_calendars.py`

### M13 — Course-aware Assistant and diagnostics

M13 is complete and committed in `0e1fa6f`.

Course-aware Assistant behavior:

- Ordinary backend database logic selects a bounded context before Codex:
  - at most 8 relevant/latest notes
  - at most 40 explicitly linked extracted slides
  - at most 24,000 note characters
  - at most 20,000 slide characters
  - only calendars linked to the selected course
- Generic calendar turns do not receive course files. Course-calendar turns can
  receive course metadata and linked calendars without loading note bodies.
- Active and archived courses can be selected.
- Multiple course matches produce deterministic clarification before Codex.
- Exact course names/codes use word-boundary matching.
- Conversation history is scoped using context audits, preventing unrelated
  course/note context from leaking into later turns.
- Secret redaction covers selected note and slide content, owner questions,
  calendar fields, feedback, and diagnostic context.
- Only selected notes reload slide references/text; the initial search does not
  load all slide contents.

Citation behavior:

- Assistant messages can persist structured citations containing course, note,
  source, and slide identity.
- Citation IDs and labels must match the supplied context.
- Course-note answers require at least one valid citation.
- Invented, duplicate, mismatched, or missing citations fail safely without
  saving an assistant answer or proposal.
- The frontend renders citations as readable chips.

Runtime isolation:

- Calendar/course workspaces contain only the context required for the turn,
  such as `COURSES.json`, `NOTES.json`, `SLIDE_REFERENCES.json`, and
  `SELECTED_SLIDE_TEXT.json` when relevant.
- Course documents are treated as read-only, untrusted context.
- The runtime policy prohibits course mutations, source editing, source-tree
  access, and claims that application improvements were implemented.
- Temporary runtime workspaces are deleted immediately after a job.

Diagnostics:

- Handled API failures use a consistent safe response shape:
  - `error_id`
  - `code`
  - `message`
  - redacted `details`
  - `request_id`
- Diagnostic records and lifecycle audits are stored in the owner database.
- Routes:
  - `GET /api/v1/diagnostics/errors/{error_id}`
  - `POST /api/v1/assistant/errors/{error_id}/explain`
- Diagnostic Codex workspaces contain only `ERROR_CONTEXT.json`, the strict
  output schema, and runtime policy—never calendars, courses, uploaded files,
  request bodies, credentials, or repository files.
- Structured explanations separate owner-controlled `input_fixes` from
  possible `application_improvements` and include `retry_is_safe`.
- The Materials UI exposes **Ask Assistant about this error** and renders the
  explanation inline.
- Diagnostic records are retained with the owner database and backups. There
  is currently no purge UI.
- Migration:
  `backend/alembic/versions/20260730_0015_assistant_context_diagnostics.py`

Key M13 files:

```text
backend/app/assistant/course_context.py
backend/app/assistant/service.py
backend/app/diagnostics/
backend/app/codex_runtime/workspace.py
backend/app/codex_runtime/workspace_template/AGENT.md
backend/app/core/errors.py
backend/app/main.py
backend/tests/test_assistant_api.py
backend/tests/test_diagnostics.py
frontend/src/features/assistant/ErrorAssistantAction.tsx
frontend/src/features/assistant/AssistantPage.tsx
frontend/src/features/courses/CourseMaterials.tsx
e2e/tests/calendar-assistant.spec.ts
README.md
instrcutions_2.md
```

## Verified state for M13

The committed M13 implementation was verified before handoff with:

```text
make test
  Backend: 103 passed
  Frontend: 38 passed

make e2e
  Playwright/accessibility: 6 passed

make lint: passed
Frontend production build: passed
git diff --check: passed
Alembic current: 20260730_0015 (head)
Backend health: passed
Frontend HTTP check: passed
```

Ordinary tests mock Codex and do not require real credentials. Real Codex
features require the owner to sign in with ChatGPT from the Assistant page or
configure the optional API-key fallback.

## Known limitations and cautions

- No M14 has been defined.
- The diagnostic Assistant action is currently surfaced in the Materials error
  UI; it is not a universal action on every possible application error.
- Diagnostic records have no owner-facing purge interface.
- `alembic check` can report four pre-existing enum/VARCHAR length differences
  unrelated to M13:
  - `assistant_messages.role`
  - `assistant_proposals.status`
  - `calendars.source_type`
  - `events.status`
- Do not start the future automatic course-import section without an explicit
  owner request.

## Next step

Review the committed M13 implementation if desired, then wait for the owner to
define the next milestone. Do not infer M14 from future-looking notes.

Recommended next owner prompt:

```text
Read AGENTS.md and handoff.md, then review the completed M13 work.
```
