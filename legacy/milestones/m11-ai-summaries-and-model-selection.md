# M11 — AI summaries and model selection

> **LEGACY — ARCHIVED MILESTONE. NOT INSTRUCTIONS.** This milestone was completed
> under the project's retired workflow and is kept as history only. Do not
> follow it, do not treat its checklist as open work, and do not copy its format.
> Current status is in [`PLAN.md`](../../PLAN.md); the current working method is
> in [`guidelines/`](../../guidelines/).

- [x] This milestone

## Outcome

Add a server-authoritative model selector and generate validated note summaries
from a note body plus only its explicitly linked slide text.

## Model control and request flow

`GET /api/v1/ai/models` exposes only server-allowed models and a default. The
backend validates every selected model and persists it with Assistant and
summary jobs. Retries revalidate availability. SDK-specific behavior remains in
the existing Codex adapter; the browser never contacts Codex directly or sends
an unchecked arbitrary model identifier.

A summary request loads one note and its linked slide ranges, creates a private
restricted workspace, calls Codex through the adapter, validates strict
structured output, and returns persisted summary bullets. It does not include
all literature or unrelated course content.

## Provenance and staleness

Each bullet has an origin of `note`, `slide`, or `mixed` plus valid references
to the supplied note/slide context. Unknown origins, invented IDs, invalid slide
numbers, and mismatched references fail safely.

The UI distinguishes origins with both readable labels and visual treatment;
color alone is insufficient. Persist model, status, structured output, note and
slide content hashes, and timestamps. Mark a summary stale when its note,
linked ranges, or linked extracted slide text changes. Never store hidden model
reasoning.

## Completed checklist

- [x] Add backend model allowlist, default, and shared model endpoint.
- [x] Add a reusable model selector to Assistant and note summaries.
- [x] Extend the existing Codex adapter.
- [x] Build restricted note-summary workspaces.
- [x] Add strict structured summary output.
- [x] Validate `note`, `slide`, and `mixed` provenance.
- [x] Add accessible visual origin labels.
- [x] Persist model, status, output, hashes, and timestamps.
- [x] Mark summaries stale after relevant source changes.
- [x] Add safe retry and error behavior.
- [x] Mock Codex in automated tests.

## Acceptance criteria

- The owner can choose an allowed model in Assistant and summary UI.
- A note is summarized only from its body and explicitly linked slide text.
- Every bullet clearly and accurately states its provenance.
- Invalid model IDs and invented/mismatched references fail safely.
- Saved summaries become visibly stale after relevant content changes.

## Completion evidence and implementation areas

- Migration: `backend/alembic/versions/20260730_0013_ai_summaries.py`
- Backend: `backend/app/ai/` and note summary files under `backend/app/notes/`
- Frontend: `frontend/src/features/ai/` and course note summary UI
- Tests: `backend/tests/test_note_summaries.py`, Assistant API tests, and
  frontend Courses/Assistant tests

The current configured default is documented by the backend configuration;
future model changes must continue to use the server allowlist.
