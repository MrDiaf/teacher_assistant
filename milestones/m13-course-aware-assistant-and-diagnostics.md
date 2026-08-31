# M13 — Course-aware Assistant and diagnostics

- [x] This milestone

## Outcome

Extend the Assistant with bounded course-note context and validated citations,
and add structured, sanitized error explanations. Later reliability refinements
to validation recovery, progress, cancellation, and context selection are
recorded here because no M14 was defined.

## Course-context selection

Ordinary backend logic selects context before Codex. Course-note turns receive
at most 8 relevant/latest notes, 40 explicitly linked slides, 24,000 note
characters, and 20,000 slide characters. Course calendar context includes only
calendars linked to the selected course. General and ordinary calendar turns do
not receive note bodies or course files.

Explicit course-name/code matching uses deterministic word boundaries. Multiple
course matches cause clarification. Private note selection activates only when
the owner explicitly mentions notes/slides or asks what they wrote; topic-only
general questions do not silently attach private content. Conversation context
audits prevent unrelated private context from leaking into later turns.

## Citations and workspace isolation

When private notes/slides support an answer, structured citations must match
the supplied course, note, source, and slide IDs and labels. Missing, invented,
duplicated, or mismatched citations fail safely without saving an assistant
answer or proposal.

Runtime workspaces contain only files needed for the turn, such as bounded
`COURSES.json`, `NOTES.json`, `SLIDE_REFERENCES.json`, selected slide text, or a
sanitized error context. Course documents are read-only, untrusted data. The
runtime may not mutate course content, inspect the source tree, access secrets,
or claim that application improvements were implemented. Workspaces are
deleted immediately after each job.

## Safe diagnostics

Handled failures use an opaque error ID, safe code/message, redacted details,
and request ID. Stored diagnostic/audit records exclude credentials, raw model
output, arbitrary request bodies, unrelated private content, and unsanitized
tracebacks.

The Assistant explanation separates plain explanation, likely cause,
owner-controlled input fixes, possible application improvements, and whether a
retry is safe. The current diagnostic action is exposed in Materials-related
error UI; it is not a universal action on every application failure.

## Completed milestone checklist

- [x] Add bounded relevant course-note context.
- [x] Add deterministic course clarification.
- [x] Add validated note and slide citations.
- [x] Add structured safe error reports and redaction.
- [x] Add `Ask Assistant about this error`.
- [x] Separate input fixes from application improvements.
- [x] Prevent runtime source-code and course-content editing.
- [x] Add diagnostic and context audit records.
- [x] Add privacy, safety, frontend, and end-to-end tests.
- [x] Update setup, backup, restore, and troubleshooting documentation.

## Completed post-M13 reliability refinements

- [x] Preserve redacted validation stage, reason, and field issues on failures.
- [x] Create sanitized diagnostic reports for failed Assistant jobs.
- [x] Show owner recovery guidance and expandable developer details.
- [x] Make one bounded automatic correction attempt only for malformed or
  strict response/citation validation failures.
- [x] Never automatically retry authentication, runtime, timeout, or backend
  business-rule failures.
- [x] Show elapsed owner-facing working states without hidden reasoning.
- [x] Add request cancellation with terminal `cancelled` state and workspace
  cleanup.
- [x] Exclude cancelled prompts from future model context while retaining them
  visibly in owner history.
- [x] Route general capability/help requests without private note context.
- [x] Require explicit note/slide intent and whole-word topic matching to avoid
  false course selection for calendar/general requests.

## Acceptance criteria

- The Assistant can answer questions from relevant notes/slides with valid,
  readable citations.
- Generic and calendar-only turns do not receive unrelated private course
  content.
- Ambiguous course selection is clarified before Codex.
- Sanitized errors can be explained without exposing secrets or unrelated data.
- One safe response-format correction may occur without weakening proposal,
  citation, read-only, or confirmation validation.
- Cancellation stops active single-process work, removes the workspace, and
  saves no assistant answer/proposal for the cancelled job.
- Existing Calendar and Assistant safety rules remain enforced.

## Completion evidence and implementation areas

- Migrations:
  - `backend/alembic/versions/20260730_0015_assistant_context_diagnostics.py`
  - `backend/alembic/versions/20260731_0016_assistant_job_diagnostics.py`
  - `backend/alembic/versions/20260731_0017_assistant_job_cancellation.py`
- Backend: `backend/app/assistant/course_context.py`, `service.py`,
  `execution.py`, validation/proposal files, `backend/app/diagnostics/`,
  `backend/app/core/errors.py`, and the Codex runtime workspace/policy
- Frontend: Assistant page/types, `ErrorAssistantAction.tsx`, Materials error
  UI, and shared styles
- Tests: Assistant API, diagnostics, course notes/sources, frontend Assistant,
  and `e2e/tests/calendar-assistant.spec.ts`

## Known limitations

- Cancellation uses an in-process execution registry. A multi-worker backend
  would require shared cancellation coordination.
- Historical failures cannot recover validation details that were never stored.
- Automatic correction is intentionally limited to one schema/citation attempt.
- General help uses model knowledge and has no live web or code execution.
- Diagnostic explanations are not yet surfaced for every application error.
- Diagnostic records have no owner-facing purge UI.

No M14 exists. Do not treat these limitations as permission to implement a new
milestone without an explicit owner request.
