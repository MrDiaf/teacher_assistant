# Assistant handoff

Current state: M21F is complete. Existing read-only chat, validated proposals,
linked batches, course context, diagnostics, progress, cancellation, and
browser-local drafts are preserved. Assistant consumes Calendar, Courses, and
Platform only through public contracts. The proposal coordinator still owns
one shared transaction: Calendar commands flush without committing, then
Assistant and Calendar state commit together; failures roll back before a
Platform-owned diagnostic transaction records only bounded sanitized details.

Verification on 2026-09-30: `make test-module MODULE=assistant` passed 106
backend tests, 44 frontend tests, and the focused browser scenario. `make test`
passed 251 backend and 117 frontend tests plus boundary, contract, and
data-safety gates; `make lint`, full and module production builds, and all 19
browser/accessibility scenarios passed. The focused Docker host answered on
both ports and migrated a fresh database to `20260908_0021 (head)`.

Assistant owns its errors, stylesheet, job-error/proposal components, scoped
backend fixture, and focused browser scenario. Its focused host selects real
Calendar/Courses providers and Platform AI/diagnostics; ordinary tests override
Codex and use no credentials or network model request. Settings exposes shared
AI authentication independently, while `/assistant/auth*` remains compatible.
Cancellation and timeout workspace deletion, stale permissions, unknown and
bulk actions, read-only protection, repeated confirmation, draft persistence,
and backend-reported completion are covered.

Next Assistant work: none. M21G is the next selected milestone and owns Inbox
and contributed Settings boundaries; do not start M22.
