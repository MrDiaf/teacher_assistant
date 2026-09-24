# Platform handoff

Current state: M21B and the first three M21C items are complete. Matching strict
Python and TypeScript catalogs define stable module/page order, dependency
capabilities, route identities, Settings contribution identities, and lifecycle
identities without import paths or executable names.

`make check-module-contract` verifies frontend/backend catalog agreement,
identity and dependency agreement with `architecture/module-boundaries.json`,
and rejection of deliberate drift. Typed tests reject duplicate IDs/orders,
duplicate dependencies/capabilities, self/unknown dependencies, missing
capabilities, cycles, duplicate contributions, and extra executable-looking
fields. `make test` runs this gate.

Every current owner now exposes an explicit page/router entry. Platform's
frontend catalog binds page IDs to statically imported components; `App.tsx`
and `AppShell.tsx` render and navigate those registrations. Platform's backend
catalog binds route IDs to statically imported FastAPI routers; `main.py`
includes them through one validated assembly function. Code-entry validation
rejects missing/unknown/duplicate contributions and duplicate HTTP method/path
pairs. Test-only entries can be assembled and mounted without changing shell
rendering or importing unrelated production modules.

The canonical extension procedure is in the Platform README. In brief, update
both mirrored metadata catalogs and closed ID types, bind code in the owner
`entry.ts`/`entry.py`, add that entry to the matching static Platform catalog,
update the exact ownership/dependency/public-entry boundary declarations, and
add contract/composition coverage. Production requires every registered entry;
selective tests instead use a matching synthetic catalog and explicit entry
tuple. Settings-panel metadata is validated but remains code-unbound until M21G;
`enabled_by_default` is not a runtime switch before M21H.

Each public backend entry now binds its declared lifecycle identities to
explicit startup functions. Platform runs only the supplied entries in stable
effect order, retains successful cleanup callbacks, and unwinds them in reverse
after normal shutdown or a later startup failure. Every cleanup has a
five-second hard bound; startup cleanup preserves the original startup error.
The full app supplies every registered entry, initializes existing private roots
before starting the ICS/mail schedulers, and retains the existing Assistant and
Codex shutdown behavior. Selective test assembly starts no unselected hook.

Documents now re-exports a typed recovery contribution containing only its
stable manifest/archive/root identities, format introduction, and safety limits.
Platform's existing coordinator consumes it for archive creation, manifest
verification, format-2 compatibility, restore, and rollback; quiescence,
PostgreSQL coordination, restore order, and live paths remain Platform-owned.

Platform now owns the shared FastAPI application factory used by both the full
catalog and focused host. Dependency-closed selection accepts only an explicit
allowlisted module ID; the Documents host assembles the real Platform and
Documents backend entries and only their routes/lifecycle hooks. The frontend
uses the same `RegisteredApplication` shell with matching real page entries.
Ordinary startup remains the complete catalog and contains no fixture provider.

Root `dev-module`, `logs-module`, `down-module`, and `test-module` commands use
the existing images/configuration plus a bounded Compose override. Documents is
the only supported ID. Its development stack uses ports `15173`/`18000`, a
separate Compose project, isolated PostgreSQL, and project-scoped private-data
volumes; invalid IDs fail before Compose starts.

Feature code now imports the existing icon/modal, API error, browser persistence,
and model-selection primitives through narrow Platform façades. Persistence no
longer imports Calendar or Courses types, the version-1 storage envelope is
unchanged, and focused tests cover legacy state restoration. Root tokens,
shell/navigation, accessibility, responsive-shell, and placeholder styling now
have a Platform-owned stylesheet; feature CSS remains in the legacy stylesheet.
Generic enum serialization moved out of Calendar and into Platform database
infrastructure. Thin backend Platform façades publish the existing AI/runtime
and diagnostic interfaces for M21F to restructure behind. No M21B boundary
exception remains. The backend Platform allowance now names exact consumed
configuration, error, database, AI, diagnostic, and registration modules;
negative fixtures reject feature imports of backend assembly or frontend shell
internals. Documents-owned fixture/browser/provider separation, non-Documents
scoped feature CSS, and deeper M21F AI/diagnostic separation are still
unimplemented.

Verification: [M21A baseline](../baseline.md). Shared cautions and active
application status remain in the root `handoff.md`.

Item-3 verification on 2026-09-11: `make test-module MODULE=documents` passed 26
backend and 26 frontend host/contract tests. `make test` passed 228 backend and
107 frontend tests plus boundary, catalog-agreement/drift, and data-safety gates;
`make lint` and full/module-mode production frontend builds passed. The focused
stack started beside the owner stack and exposed only Platform/Documents routes
on its isolated ports; temporary containers and test/build volumes were removed.

Next step: M21C is active. Its next incomplete checklist item is Documents-owned
fixture and backend/frontend/browser scenario separation with real API/storage
and fake/provider contract coverage. M22 remains inactive until the M21A-M21I
refactoring sequence is complete.
