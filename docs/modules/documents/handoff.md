# Documents handoff

Current state: M21C is complete. M21
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

Final verification: `make test-module MODULE=documents` passed 34 backend, 29
frontend, and 2 browser tests. Backend tests use the real focused host, truncate
only Documents tables, and assign a private per-test source root. Unit Compose
mounts no private roots; browser Compose mounts only isolated Documents storage.
The test-only frontend provider and reversible browser route validate the
Documents API surface and reject undeclared requests without production wiring.

The warm focused command measured 37.24 seconds outer wall time (8.40-second
backend runner, 2.04-second frontend runner, and 3.7-second browser runner).
This includes host contracts and browser startup beyond the M21A representative
file timings, so no direct speedup is claimed. The boundary manifest contains
no Documents exception, production scans passed, and the deliberate cross-owner
fixtures were rejected.

Final full checks passed 228 backend and 108 frontend tests, all 13 full
browser/accessibility scenarios, lint, full and module-mode production builds,
data-safety checks, and the exact coordinated relocation/backup/restore drill.
The relocation copier now ignores deleted tracked paths so an owned test-file
move is reproducible from an uncommitted worktree. All temporary test stacks and
volumes were removed.

Next Documents work: none until a later Documents milestone is explicitly
selected. M22-M24 remain inactive. The next planned project milestone is M21D,
which requires explicit owner selection.
