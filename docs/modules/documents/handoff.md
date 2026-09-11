# Documents handoff

Current state: M21C is active and its first two checklist items are complete. M21
project/tag CRUD, private source creation/downloads, deletion compensation, and
coordinated recovery behavior remain unchanged; M22-M24 remain unimplemented.
The M21B public API/page entries remain the sole production composition imports,
and the backend entry still registers unchanged private storage initialization.
Documents now owns its five application/storage errors instead of defining them
in Platform's common error module. Its existing responsive feature CSS moved
unchanged out of the global stylesheet and loads through the frontend public
entry; the delete dialog now uses Documents-owned rather than Courses-specific
selectors.

Documents now declares its stable manifest key, archive filename/root,
format-3 introduction, and archive limits in a typed Platform recovery contract
re-exported by its public backend entry. The Platform coordinator consumes that
declaration for archive creation, manifest construction/verification, and
restore while retaining database/filesystem quiescence, format-2 empty-root
compatibility, restore order, and rollback paths. The declaration exposes no
live path, session, repository, or executable callback.

Verification: [M21A baseline](../baseline.md). Completed feature acceptance is
in [M21](../../../milestones/m21-durable-documents-foundation.md).

Current verification: Documents-focused backend tests passed 8 tests against
isolated PostgreSQL/storage; its frontend suite passed 2 tests. `make test`
passed 217 backend and 97 frontend tests plus boundary, catalog-drift, and
data-safety gates. The focused archive suite passed 18 tests, including exact
recovery identities, format-2 compatibility, unsafe contributions/archives,
and document publish-failure rollback. `make data-relocation-test` reproduced
the coordinated database/private-file restore, and `make lint` passed. The
production frontend build and all 12 isolated E2E/accessibility scenarios last
passed with the first M21C item.

Next Documents work: continue M21C with its third checklist item—implement the
shared module host and initial focused Docker commands. Do not begin fixture
separation, M21D, or M22 automatically.
