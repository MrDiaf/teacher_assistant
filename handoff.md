# Teacher Assistant development handoff

Updated: 2026-08-31

## Start here

Read these files completely before planning or changing code:

1. `AGENTS.md`
2. `instructions.md`
3. `handoff.md`
4. The owner-selected file under `milestones/`
5. The relevant implementation and tests

The milestone status index in `instructions.md` is authoritative. The selected
milestone file is the implementation boundary for a development session.
`instructions_1_comleted.md` and `instrcutions_2.md` are retained only as legacy
source specifications; do not follow their stale starting commands.

Run `git status --short` before editing and preserve all owner work. Do not
commit, push, merge, rebase, delete branches, or discard changes unless the
owner explicitly asks.

## Current state

- Git `HEAD`: `a14781d seems like it is fixed now`
- M1 through M13 are complete.
- The post-M7 linked Assistant proposal-batch milestone is complete.
- The post-M13 Assistant diagnostics, general-helper routing, bounded automatic
  correction, working-state display, cancellation, and false course-note
  matching refinements are complete and committed in `a14781d`.
- No M14 is defined or active. Known limitations are not an implied milestone.
- The current uncommitted changes are documentation-only: the new general
  instructions, individual milestone files, and updated reading/handoff rules.
- Docker development services are running:
  - frontend: `http://localhost:5173`
  - backend: `http://localhost:8000`
  - PostgreSQL: healthy
- Alembic is at `20260731_0017 (head)`.
- `.openai/hosting.json` is absent. This is a self-hosted Docker application,
  not a Sites deployment.

Recheck instead of trusting this snapshot at the start of the next session:

```bash
git status --short
docker compose -f compose.yml -f compose.dev.yml ps
docker compose -f compose.yml -f compose.dev.yml exec -T backend alembic current
```

## Implemented product surface

- Calendar: local/imported/subscribed calendars; day, week, and month views;
  recurrence; drag/move/resize; search/filter; read-only protection; ICS import
  and subscriptions.
- Assistant: private conversations, bounded calendar/course context, model
  selection, validated calendar proposals, separate confirmations, linked
  creation batches, retries, diagnostics, progress, and cancellation.
- Courses: manual CRUD/archive/restore, private Literature and Slides storage,
  extraction, notes and slide references, AI summaries with provenance,
  course-linked calendars, and course-aware Assistant answers.
- Dashboard, Study Plan, and Settings remain placeholder modules unless the
  owner defines a new milestone.

The permanent safety and architecture rules are in `AGENTS.md` and
`instructions.md`. Do not duplicate or weaken them in a new milestone.

## Most recent completed work

The reliability work committed in `a14781d`:

- performs exactly one bounded automatic correction when the first Codex
  response is malformed or fails response/citation validation;
- never automatically retries authentication, runtime, timeout, or backend
  business-rule failures;
- displays elapsed working states without exposing hidden reasoning;
- lets the owner cancel active work and records a terminal `cancelled` job;
- removes cancelled workspaces, saves no cancelled answer/proposal, and excludes
  cancelled prompts from later model context;
- prevents generic word/substring matches from attaching unrelated private
  course notes to calendar or general-help turns;
- gives ordinary calendar turns all relevant calendars while omitting course
  note/slide files;
- preserves confirmation, idempotency, read-only enforcement, citation
  validation, redaction, and runtime isolation.

Important implementation areas:

```text
backend/app/assistant/course_context.py
backend/app/assistant/execution.py
backend/app/assistant/service.py
backend/app/codex_runtime/workspace.py
backend/app/codex_runtime/workspace_template/AGENT.md
backend/app/core/errors.py
backend/tests/test_assistant_api.py
frontend/src/features/assistant/AssistantPage.tsx
frontend/src/features/assistant/AssistantPage.test.tsx
e2e/tests/calendar-assistant.spec.ts
```

## Last full verification recorded

The latest implementation handoff recorded:

```text
make test
  Backend: 109 passed
  Frontend: 39 passed

make e2e
  Playwright/accessibility: 8 passed

make lint: passed
Frontend production build: passed
git diff --check: passed
Alembic current: 20260731_0017 (head)
Backend health: passed
Frontend HTTP check: passed
```

Ordinary tests mock Codex. Real Codex features require private ChatGPT sign-in
from Assistant or the optional configured API-key fallback.

## Known limitations and cautions

- No M14 has been defined.
- Historical Assistant failures cannot recover validation detail that was never
  stored; retrying creates current structured diagnostics if failure repeats.
- Automatic correction is limited to one response-schema/citation retry.
- Cancellation coordination is in-process and assumes the current
  single-process backend; multiple workers would need shared coordination.
- General help has no live web access, code execution, clipboard control, or
  interactive editor.
- Private course content is attached only for explicit note/slide intent; an
  ambiguous topic-only question uses general model knowledge.
- `Ask Assistant about this error` is not exposed for every application error.
- Diagnostic records have no owner-facing purge UI.
- `alembic check` may report four pre-existing enum/VARCHAR length differences:
  `assistant_messages.role`, `assistant_proposals.status`,
  `calendars.source_type`, and `events.status`.
- Automatic LMS/course import, assignments, Study Plan, and new modules require
  an owner-defined milestone.

## Next step

The documentation is now organized for milestone-based handoffs. After review,
wait for the owner to define or select the next milestone; do not infer M14.

Recommended next prompt:

```text
Read AGENTS.md, instructions.md, handoff.md, and the selected milestone file.
Implement only that milestone and stop after its acceptance criteria are verified.
```
