# Assistant handoff

Current state: completed read-only chat, validated proposals, linked batches,
course context, diagnostics, progress, cancellation, and browser-local drafts
are preserved. M21A changed no runtime policy, action, context limit, or data.
M21B now routes Assistant API/page composition through explicit public entries;
the backend entry registers bounded execution-registry shutdown.
M21D routes Calendar reads, permission revalidation, and allowed mutations
through Calendar's typed public ports. The proposal coordinator still owns one
shared database transaction: Calendar commands flush without committing, then
Assistant and Calendar state commit together; failures roll back before safe
failure recording. The port exposes no calendar deletion, protection change,
bulk deletion, repository, or session.

Verification: [M21A baseline](../baseline.md). Feature evidence is linked from
[M13](../../../legacy/milestones/m13-course-aware-assistant-and-diagnostics.md) and
[M19](../../../legacy/milestones/m19-frontend-navigation-and-draft-persistence.md).

M21E moved course context onto Courses' public contract. Assistant still owns
when course context applies and which notes are relevant; it no longer queries
Courses tables. The existing course-aware Assistant tests pass unchanged
against the real contract.

Next Assistant work: M21F. It removes the remaining Platform AI/diagnostic
internals and separates shared AI/diagnostics.
