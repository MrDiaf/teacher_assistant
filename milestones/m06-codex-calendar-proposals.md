# M6 — Codex calendar proposals

- [x] This milestone

## Outcome

Allow the Assistant to propose narrowly defined calendar mutations while
keeping validation, permission checks, owner confirmation, and execution under
backend control.

## Allowed proposal operations

- `create_calendar`
- `update_calendar` for `name`, `description`, or `color` only
- `create_event`
- `update_event`
- `delete_event` for individual writable events

Unknown operations are rejected. Codex may not change `is_read_only` or
`source_type`, delete a calendar, bulk-delete events, invent target IDs, or
affect more than 10 events in one executable proposal.

## Confirmation and execution rules

Every mutation begins in `awaiting_confirmation`. The UI shows the calendar,
event, before/after values where applicable, time and timezone, recurrence
scope, warnings, and affected count. The owner explicitly confirms or rejects.

Immediately before execution, the backend revalidates existence, writability,
event freshness, time values, expiry, and prior execution. Confirmation is
idempotent; double confirmation cannot duplicate an event. Codex never updates
the database directly and never claims success before service execution.

## Completed checklist

- [x] Add strict proposal schemas and unknown-action rejection.
- [x] Add create- and update-calendar proposals.
- [x] Add create-, update-, and delete-one-event proposals.
- [x] Add confirmation, rejection, and revision UI.
- [x] Revalidate proposals before execution.
- [x] Execute confirmed actions through calendar services.
- [x] Enforce read-only and recurrence-scope restrictions.
- [x] Add proposal expiry and idempotency.
- [x] Store safe proposal audit data without hidden reasoning.
- [x] Add safety and failure-feedback tests.

## Acceptance criteria

- Codex can propose allowed changes, but no calendar data changes before owner
  confirmation.
- Read-only calendars and their events cannot be changed through any proposal.
- Codex cannot delete calendars or bulk-delete events.
- Ambiguous destructive requests require clarification.
- Confirmation is idempotent and execution results are accurately reported.

## Completion evidence and implementation areas

- Migrations:
  - `backend/alembic/versions/20260719_0007_assistant_proposals.py`
  - `backend/alembic/versions/20260720_0008_assistant_error_feedback.py`
- Backend: Assistant proposal schemas, validation, repository, and service under
  `backend/app/assistant/`
- Frontend: proposal cards and actions in `AssistantPage.tsx`
- Tests: Assistant API, calendar API, and end-to-end proposal safety coverage

Plans containing more than 10 independent creations are deferred to the
post-M7 linked-batch milestone; the per-proposal limit remains permanent.
