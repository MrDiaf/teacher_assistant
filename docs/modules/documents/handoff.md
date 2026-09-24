# Documents handoff

Current state: M21C is active and its first three checklist items are complete. M21
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

The shared module host now selects the dependency closure for the allowlisted
`documents` ID and assembles the real Platform and Documents entries. Its
backend exposes only their routes and lifecycle hooks; its frontend renders the
real Documents page through the existing shell. Root Docker commands provide an
isolated Compose project, PostgreSQL database, private-data volumes, and default
UI/API ports `15173`/`18000`, so it can run beside the owner application.

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

Item-3 verification passed 26 backend and 26 frontend focused host/contract
tests. `make test` passed 228 backend and 107 frontend tests plus boundary,
catalog-drift, and data-safety gates. `make lint`, full and module-mode frontend
production builds, live isolated startup, route selection, and invalid-ID
rejection passed. The focused stack was stopped and temporary test/build volumes
were removed. The initial focused command does not yet own the Documents
CRUD/storage fixture or browser/provider scenarios; that is item 4.

Next Documents work: continue M21C with its fourth checklist item—separate
Documents fixtures and backend/frontend/browser scenarios while retaining real
API/storage coverage and fake/provider contract checks. Do not begin boundary
cleanup, M21D, or M22 automatically.
