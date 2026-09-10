# Assistant handoff

Current state: completed read-only chat, validated proposals, linked batches,
course context, diagnostics, progress, cancellation, and browser-local drafts
are preserved. M21A changed no runtime policy, action, context limit, or data.
M21B now routes Assistant API/page composition through explicit public entries;
the backend entry registers bounded execution-registry shutdown.

Verification: [M21A baseline](../baseline.md). Feature evidence is linked from
[M13](../../../milestones/m13-course-aware-assistant-and-diagnostics.md) and
[M19](../../../milestones/m19-frontend-navigation-and-draft-persistence.md).

Next Assistant work: M21F after Calendar and Courses contracts exist. It removes
foreign internals and separates shared AI/diagnostics. The app-wide next step is
M21B's remaining composition-test and boundary-tightening subtask.
