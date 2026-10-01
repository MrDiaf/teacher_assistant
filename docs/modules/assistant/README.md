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

Assistant application errors live in `app.assistant.errors`; its stylesheet is
`frontend/src/features/assistant/styles.css`. Job-error and proposal rendering
are separate components from page orchestration. Backend tests live under
`backend/tests/assistant/` and mount the dependency-closed real host; the owned
browser scenario is `e2e/tests/assistant.spec.ts`.

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

No feature consumes Assistant internals. Sanitized error explanations use the
Platform-owned `platform/diagnostics` contribution and
`/api/v1/diagnostics/errors/{id}/explain`; the old Assistant route remains a
compatibility delegate.
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
All AI/runtime/diagnostic access now goes through `app.platform.ai`,
`app.platform.diagnostics`, `platform/ai`, or `platform/diagnostics`. There is
no M21F boundary exception. Assistant authentication routes remain compatible
delegates to the same Platform auth manager exposed at `/api/v1/ai/auth*`.

## Current commands

```bash
make dev
make dev-module MODULE=assistant
make test-module MODULE=assistant
make down-module MODULE=assistant
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/assistant tests/test_codex_runtime.py tests/test_diagnostics.py
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/assistant
make test
make e2e
```

Codex is mocked in ordinary tests. The focused host closes over Platform,
Calendar, Courses, and Assistant, presents only the Assistant page, mounts the
real provider routes and lifecycles, uses isolated PostgreSQL and course
storage, and makes no real model request. See the [M21A baseline](../baseline.md).
