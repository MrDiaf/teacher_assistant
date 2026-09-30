# Assistant module

## Ownership and current locations

Assistant owns conversations/messages, context selection policy, jobs,
proposals/action records, validation, confirmation/rejection/revision,
cancellation/progress, audit records, UI, drafts, and tests. Current code is in
`backend/app/assistant/` and `frontend/src/features/assistant/`. Assistant tables
are `assistant_conversations`, `assistant_messages`, `assistant_jobs`,
`assistant_proposals`, `assistant_proposal_actions`, and
`assistant_context_audits`; migrations 0006-0009 and Assistant portions of
0015-0017 are owner content.

Assistant has no durable file root. Runtime workspaces and authentication are
Platform services and are not Assistant data.

## Required public contracts

- `backend/app/assistant/entry.py` and `frontend/src/features/assistant/entry.ts`
  contribute the existing routes and page through Platform composition.
  The backend entry also contributes bounded execution-registry shutdown.
- Assistant consumes Calendar query/revalidation/restricted-command ports and
  Courses' bounded context port. It receives typed values/errors only.
- Platform provides model allowlisting/authentication, Codex execution,
  tool-disabled private workspaces, redaction, and diagnostic recording through
  narrow interfaces. Courses may consume these without importing Assistant.

No feature should consume Assistant internals. The current reusable
`ErrorAssistantAction` becomes a Platform diagnostic contribution in M21F.
Assistant owns proposal permissions and state-machine errors in addition to
propagating Calendar/Courses contract errors. Runtime output remains untrusted.
Proposal confirmation requires the explicit cross-module coordinator: one
transaction covers permission revalidation, all Calendar actions, action
records, proposal state, and job state; failures roll back Calendar changes
before a separately committed safe failure record.

## Dependencies and migration debt

Assistant's approved dependencies are Calendar, Courses, and Platform public
contracts. M21D removed every direct Calendar ORM/repository/schema/service
import and M21E removed every direct Courses model and repository import:
`course_context.py` keeps the relevance and selection policy and asks
`app.courses.public` for bounded, identified excerpts and linked calendar IDs.
The remaining direct Platform AI/diagnostic imports are M21F exceptions. Its frontend API error handling and shared model UI
now use Platform façades; deeper AI runtime/diagnostic internals remain M21F
debt. Assistant CSS remains global until M21F.

## Current commands

```bash
make dev
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/test_assistant_api.py tests/test_codex_runtime.py tests/test_diagnostics.py
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/assistant
make test
make e2e
```

Codex is mocked in ordinary tests. These are not yet isolated module-host
commands. See the [M21A baseline](../baseline.md).
