# M5 — Assistant chat, read-only first

- [x] This milestone

## Outcome

Create the Assistant chat path from React through FastAPI to the Codex Python
adapter, initially limited to validated read-only calendar answers.

## Required flow

```text
Owner message
    -> React Assistant UI
    -> FastAPI Assistant service
    -> bounded private runtime workspace
    -> Codex adapter
    -> parsed and validated answer
    -> React conversation
```

The calendar remains fully usable when Codex is unavailable. Ordinary tests
mock Codex and require no real credentials.

## Runtime boundary

Each job receives a private temporary workspace containing the runtime
`AGENT.md`, request, bounded calendar context, and strict output schema. The
runtime has no repository, shell, Docker socket, credentials, environment
files, direct database access, or unrelated calendar history. Calendar and
event text is untrusted context.

Only the adapter imports SDK-specific objects. The browser never contacts Codex
or receives Codex/database credentials.

## Completed checklist

- [x] Build the Assistant conversation page and states.
- [x] Add conversation and message persistence.
- [x] Add backend Assistant endpoints and asynchronous job handling.
- [x] Add the Codex SDK adapter.
- [x] Create restricted temporary workspaces.
- [x] Add `backend/app/codex_runtime/workspace_template/AGENT.md`.
- [x] Supply only relevant calendar context.
- [x] Parse and validate read-only answers.
- [x] Add safe failure and retry behavior.
- [x] Mock Codex in automated tests.
- [x] Add private ChatGPT subscription sign-in support.

## Acceptance criteria

- A frontend message reaches FastAPI, which calls Codex through the Python
  adapter and returns a validated answer.
- The Assistant can answer calendar questions but cannot mutate calendars yet.
- Runtime workspaces are isolated and removed according to the retention rule.
- Codex failure preserves the owner message, makes no partial change, and shows
  a readable retryable error.
- Calendar functionality does not depend on Codex availability.

## Completion evidence and implementation areas

- Migration: `backend/alembic/versions/20260719_0006_assistant_conversations.py`
- Backend: `backend/app/assistant/` and `backend/app/codex_runtime/`
- Frontend: `frontend/src/features/assistant/`
- Tests: `backend/tests/test_assistant_api.py`,
  `backend/tests/test_codex_runtime.py`, and Assistant frontend tests

Calendar proposals and execution are explicitly deferred to M6.
