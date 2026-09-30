# Courses handoff

Current state: all completed M8-M18 and course-calendar behavior remains in
place. M21A documented its combined ownership and dependencies without changing
files, storage, data, Markdown behavior, AI behavior, or UI.
M21B now routes all Courses-owned API/page composition through explicit public
entries without changing feature behavior.
M21D replaced course-calendar ORM/repository/service/schema and UI-internal
access with Calendar's typed public query and frontend contracts. Link records
remain Courses-owned; Calendar existence, events, and read-only values remain
Calendar-owned. Existing link/unlink and embedded Calendar behavior passed real
integration tests.

Verification: [M21A baseline](../baseline.md). Feature evidence remains in
[M18](../../../legacy/milestones/m18-codex-note-prettify.md) and its dependency
milestones rather than being copied here.

Next Courses work: M21E publishes bounded context/association contracts, scopes
Courses ownership, and removes its remaining exceptions. It requires explicit
owner selection.
