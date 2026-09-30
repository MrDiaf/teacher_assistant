# Calendar handoff

Current state: M21D is complete. Completed Calendar behavior through M7 and
linked Assistant proposal integration is preserved. Calendar owns its errors,
feature stylesheet, scoped backend/browser tests, typed query and restricted
Assistant command ports, and focused Platform+Calendar host. Courses and
Assistant consume Calendar through exact public contracts only.

Verification: [M21A baseline](../baseline.md). Historical feature acceptance is
owned by [M7](../../../legacy/milestones/m07-final-calendar-hardening.md) and
[linked batches](../../../legacy/milestones/m07a-linked-proposal-batches.md).

M21D verification passed provider, Courses, and Assistant integration coverage,
the full backend/frontend suites, lint, production builds, focused and full
browser/accessibility workflows, boundary rejection, migration-from-zero, and
isolated focused startup. Read-only, recurrence, rollback, repeated
confirmation, ICS import/subscription, filtering, view changes, editing, and
undo behavior remain covered.
The complete focused command passed 104 backend tests in 22.75 seconds, 53
frontend tests in 3.84 seconds, and 2 browser tests in 4.0 seconds; outer wall
time was 53.43 seconds including Compose startup, builds, and cleanup.

Next Calendar work: none. M21E is the next planned application milestone and
owns Courses boundaries. It requires explicit owner selection; do not start
M22.
