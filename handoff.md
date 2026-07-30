# Teacher Assistant development handoff

Updated: 2026-07-30  
Repository: `/home/ronny/Public/projects/teacher_assitant`

## Start here

1. Read `AGENTS.md` completely and follow its session-canary instruction.
2. Read `instrcutions_2.md` (the filename is intentionally misspelled).
3. Inspect the worktree before editing. Do not discard, reset, or overwrite the
   uncommitted M11 work described below.
4. Continue with one milestone only. M8, M9, M10, and M11 are complete. The next
   milestone is M12.
5. Do not commit, push, merge, rebase, or delete branches unless the owner asks.

The stale “Implement M8 only” text near the bottom of `instrcutions_2.md` has
been superseded by the owner's explicit milestone requests and the completed
M8–M11 checklists.

## Current repository and runtime state

- Current Git `HEAD`: `2f96aae M10 - notes and slides references , complete`
- M11 is implemented and verified but remains uncommitted in the worktree.
- `handoff.md` is also an uncommitted handoff artifact.
- Development services are running:
  - Frontend: `http://localhost:5173`
  - Backend: `http://localhost:8000`
  - Backend health: passing
  - PostgreSQL: healthy
- Alembic is at `20260730_0013 (head)`.
- No M12 implementation has started.
- No `.openai/hosting.json` exists. This is a self-hosted Docker application;
  do not deploy it through Sites.

Before making changes, run:

```bash
git status --short
docker compose -f compose.yml -f compose.dev.yml ps
docker compose -f compose.yml -f compose.dev.yml exec -T backend alembic current
```

## Product constraints that must remain true

- This is a single-owner application. Do not add accounts, registration,
  organizations, teams, roles, tenants, or shared profiles.
- Preserve the fixed dark-green sidebar, warm off-white background, gold
  accent, module-based shell, and existing Calendar/Assistant behavior.
- Keep development Docker-first and preserve all root Makefile commands.
- Browser code must never contact Codex directly.
- Codex must never update the database. It returns structured untrusted output;
  backend services parse, validate, and execute any allowed action.
- All Codex-generated calendar mutations require confirmation.
- Read-only calendar enforcement remains authoritative in the backend and
  database as well as the UI.
- Do not add a Codex delete-calendar action or weaken any existing assistant
  safeguards.
- Runtime Codex workspaces must not expose the source tree, Docker socket,
  credentials, environment files, database credentials, or unrelated private
  data.
- Do not implement M13 or other future systems while working on M12.

## Completed milestone summary

### M8 — Course foundation

- Manual course model, migration, CRUD, archive/restore, deletion, course cards,
  course detail shell, and tests.
- Main backend area: `backend/app/courses/`
- Main frontend area: `frontend/src/features/courses/`

### M9 — Course materials

- Separate Literature and Slides libraries.
- Safe private file storage under `data/course_content`.
- PDF, PPTX, UTF-8 text, and Markdown extraction.
- Extraction state, retry behavior, and source deletion safety.
- Main backend area: `backend/app/course_sources/`
- Migration: `backend/alembic/versions/20260730_0011_course_sources.py`

### M10 — Notes and slide references

- Note CRUD with plain-text/Markdown-safe display.
- Notes may have no slides or several explicitly linked slide ranges.
- Same-course and Slides-library validation is enforced server-side.
- Main backend area: `backend/app/notes/`
- Main UI: `frontend/src/features/courses/CourseNotes.tsx`
- Migration: `backend/alembic/versions/20260730_0012_course_notes.py`

### M11 — AI summaries and model selection

All M11 checklist items in `instrcutions_2.md` are checked and acceptance was
verified.

Implemented behavior:

- Server-authoritative shared AI model registry:
  - `GET /api/v1/ai/models`
  - Default: `CODEX_MODEL=gpt-5.6-sol`
  - Allowlist: `AI_ALLOWED_MODELS`
  - Default configured family:
    `gpt-5.6-sol,gpt-5.6-terra,gpt-5.6-luna`
  - Unknown browser-supplied IDs are rejected with `invalid_ai_model`.
- Shared React model selector is used by Assistant and note summaries.
- The selected model is remembered in browser local storage, but every request
  is revalidated by the backend.
- Assistant jobs persist their selected model. Retries reuse the stored model
  and recheck that it remains allowed.
- Note summaries persist:
  - model and status
  - validated summary JSON
  - note-content hash and linked-slide-content hash
  - safe error code/message
  - timestamps
- Summary generation uses the existing `CodexAdapter`; no second Codex
  integration was created.
- Summary workspaces contain only:
  - the note ID and body
  - extracted text from explicitly linked slide ranges
  - the runtime policy and strict output schema
- Unlinked slides, literature, other course files, calendars, credentials, and
  source code are excluded.
- Structured bullets must use one of:
  - `note`
  - `slide`
  - `mixed`
- Every bullet must contain matching source references. Invented note IDs,
  source IDs, slide numbers, unknown origins, mismatched provenance, extra
  fields, and hidden reasoning are rejected.
- UI labels provenance with text as well as color:
  - `From note` — green
  - `From slides` — blue/purple
  - `From note + slides` — gold
- Completed summaries are marked stale when the note body, linked ranges, or
  linked extracted slide text changes.
- Failed summaries persist a safe error and may be retried. Regeneration creates
  a new summary attempt.
- If a linked range has no extracted text, generation fails safely before
  Codex is called.

Key M11 backend files:

```text
backend/app/ai/
backend/app/notes/summary_models.py
backend/app/notes/summary_repository.py
backend/app/notes/summary_routes.py
backend/app/notes/summary_schemas.py
backend/app/notes/summary_service.py
backend/app/notes/summary_validation.py
backend/alembic/versions/20260730_0013_ai_summaries.py
```

Existing areas extended by M11:

```text
backend/app/assistant/
backend/app/codex_runtime/adapter.py
backend/app/codex_runtime/workspace.py
backend/app/codex_runtime/workspace_template/AGENT.md
backend/app/core/config.py
backend/app/core/errors.py
backend/app/main.py
```

Key M11 frontend files:

```text
frontend/src/features/ai/
frontend/src/features/assistant/AssistantPage.tsx
frontend/src/features/assistant/api.ts
frontend/src/features/assistant/types.ts
frontend/src/features/courses/CourseNotes.tsx
frontend/src/features/courses/api.ts
frontend/src/features/courses/types.ts
frontend/src/styles.css
```

M11 tests:

```text
backend/tests/test_note_summaries.py
backend/tests/test_assistant_api.py
backend/tests/test_codex_runtime.py
frontend/src/features/assistant/AssistantPage.test.tsx
frontend/src/features/courses/CoursesPage.test.tsx
e2e/tests/calendar-assistant.spec.ts
```

## Latest verification results

The exact M11 source state was verified with:

```text
make test
  Backend: 91 passed
  Frontend: 35 passed

make e2e
  Playwright/accessibility: 5 passed

Python Ruff: passed
Frontend TypeScript + Prettier: passed
E2E TypeScript + Prettier: passed
git diff --check: passed
Alembic current: 20260730_0013 (head)
Backend health: passed
Frontend HTTP check: passed
GET /api/v1/ai/models: passed
```

A redundant `make lint` rerun encountered a transient Microsoft Container
Registry `429` while resolving the Playwright base image. The same complete
lint command had already passed, and the exact E2E source was subsequently
rechecked successfully from the cached image.

Ordinary tests mock Codex and require no real credentials. Real summary
generation requires the owner to sign in with ChatGPT on the Assistant page or
configure the optional API-key fallback.

## Uncommitted worktree scope

The modified/untracked files at handoff are the M11 implementation,
configuration/documentation updates, M11 tests, the M11 checklist update, and
this handoff file. Treat them as intentional owner work.

Do not use destructive Git commands. In particular, do not run:

```text
git reset --hard
git checkout -- .
git clean -fd
```

Use `git status --short` and `git diff` to inspect changes. Do not assume an
untracked M11 file is disposable.

## Next milestone: M12 only

M12 is “Course-linked calendars”. Required checklist:

- Add a course-calendar relation.
- Add link and unlink API routes.
- Add calendar selection UI.
- Add the Course Calendar tab.
- Reuse existing calendar components.
- Filter the view to linked calendars.
- Preserve read-only restrictions.
- Preserve existing event behavior.
- Add tests.

Acceptance:

- One course may link to several calendars.
- Entering the course Calendar tab shows events from linked calendars.
- Events are not duplicated.
- Unlinking or deleting a course does not delete calendar data.

Suggested API shape from `instrcutions_2.md`:

```text
GET    /api/v1/courses/{course_id}/calendars
POST   /api/v1/courses/{course_id}/calendars
DELETE /api/v1/courses/{course_id}/calendars/{calendar_id}
GET    /api/v1/courses/{course_id}/events
```

Recommended M12 approach:

1. Inspect the current calendar models, repository, service, routes, frontend
   calendar components, course detail tabs, and current tests before designing
   the relation.
2. Add a pure association table/entity with foreign keys to Course and Calendar
   and a uniqueness constraint on `(course_id, calendar_id)`.
3. Deleting/unlinking a relation must never delete either calendar or its
   events. Configure ORM/database cascades accordingly and add direct tests.
4. Reuse `CalendarPage` subcomponents where practical. Do not copy the whole
   calendar feature or move business logic into React.
5. Filter by linked calendar IDs without duplicating events. Preserve the
   existing backend calendar service as the authority for all event mutations.
6. Show linked read-only calendars and their events, but keep create/edit/move/
   resize/delete controls disabled and retain backend/database protection.
7. Add migration `20260730_0014_...` revising `20260730_0013`.
8. Add backend, frontend, and Playwright coverage, run the full Docker suites,
   then check only the M12 boxes.
9. Stop after M12 and report using the exact `AGENTS.md` session-report format.

Recommended next owner prompt:

```text
Read AGENTS.md and handoff.md, then proceed with M12 only.
```
