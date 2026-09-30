# Post-M7 — Linked Assistant proposal batches

> **LEGACY — ARCHIVED MILESTONE. NOT INSTRUCTIONS.** This milestone was completed
> under the project's retired workflow and is kept as history only. Do not
> follow it, do not treat its checklist as open work, and do not copy its format.
> Current status is in [`PLAN.md`](../../PLAN.md); the current working method is
> in [`guidelines/`](../../guidelines/).

- [x] This milestone

## Outcome

Let one Assistant response prepare a large plan of independent event creations
without weakening the permanent maximum of 10 affected events per executable
proposal.

## Safety model

Linked batches are allowed only for event creation. Updates, moves, deletes,
calendar mutations, and other destructive actions cannot be batched. Each batch
has its own owner confirmation, execution status, and idempotency key.
Confirming one batch never confirms or executes another.

## Completed checklist

- [x] Allow one response to prepare more than 10 independent event creations.
- [x] Split the plan into ordered proposals capped at 10 events each.
- [x] Require separate owner confirmation for every batch.
- [x] Reject linked updates, moves, and destructive actions.
- [x] Show batch order, status, and progress in the Assistant UI.
- [x] Prevent double confirmation from duplicating events.
- [x] Add migration and backend/frontend interaction tests.

## Acceptance criteria

- The owner can review a plan such as 30 independent event creations without
  repeatedly asking for the next batch.
- Every executable proposal affects at most 10 events.
- Confirming one batch cannot execute any sibling batch.
- Linked plans cannot contain update or destructive operations.
- Repeated confirmation remains idempotent.

## Completion evidence and implementation areas

- Migration: `backend/alembic/versions/20260720_0009_linked_proposal_batches.py`
- Backend: proposal validation, repository, and execution services in
  `backend/app/assistant/`
- Frontend: linked proposal display and progress in `AssistantPage.tsx`
- Tests: Assistant API, Assistant component, and end-to-end tests

This is a completed extension of M6/M7, not permission for general bulk
mutation support.
