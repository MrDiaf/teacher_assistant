# Platform handoff

Current state: M21B-M21G are complete. Matching strict
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
tuple. Settings-panel metadata is bound to static owner contributions. Platform
Settings renders only supplied panels; Inbox owns its mailbox panel and
Platform owns its AI panel. `enabled_by_default` is not a runtime switch before
M21H.

Each public backend entry now binds its declared lifecycle identities to
explicit startup functions. Platform runs only the supplied entries in stable
effect order, retains successful cleanup callbacks, and unwinds them in reverse
after normal shutdown or a later startup failure. Every cleanup has a
five-second hard bound; startup cleanup preserves the original startup error.
The full app supplies every registered entry, initializes existing private roots
before starting the ICS/mail schedulers, and retains the existing Assistant and
Codex shutdown behavior. Selective test assembly starts no unselected hook.

Documents, Courses, and Inbox export typed recovery contributions containing
only stable manifest/archive/root identities, format introductions, and safety
limits. Platform's coordinator consumes them for archive creation, manifest
verification, compatibility, restore, and rollback; quiescence, PostgreSQL
coordination, restore order, credentials, and live paths remain Platform-owned.

Platform now owns the shared FastAPI application factory used by both the full
catalog and focused host. Dependency-closed selection accepts only an explicit
allowlisted module ID. Documents assembles Platform plus Documents; Calendar
assembles Platform plus Calendar and its ICS refresh lifecycle; Inbox assembles
Platform plus Inbox and its mail scheduler. The frontend uses the same
`RegisteredApplication` shell with matching real page and Settings entries.
Ordinary startup remains the complete catalog and contains no fixture provider.

Root `dev-module`, `logs-module`, `down-module`, and `test-module` commands use
the existing images/configuration plus bounded Compose overrides. Assistant,
Calendar, Courses, Documents, and Inbox are the supported IDs. Each development stack uses ports
`15173`/`18000`, a separate Compose project, isolated PostgreSQL, and
project-scoped private-data volumes; invalid IDs fail before Compose starts.

Feature code now imports the existing icon/modal, API error, browser persistence,
and model-selection primitives through narrow Platform façades. Persistence no
longer imports Calendar or Courses types, the version-1 storage envelope is
unchanged, and focused tests cover legacy state restoration. Root tokens,
shell/navigation, accessibility, responsive-shell, and placeholder styling now
have a Platform-owned stylesheet; each implemented feature owns its CSS.
Generic enum serialization moved out of Calendar and into Platform database
infrastructure. Thin backend Platform façades publish the shared AI/runtime
and diagnostic interfaces completed in M21F. No M21B boundary
exception remains. The backend Platform allowance now names exact consumed
configuration, error, database, AI, diagnostic, and registration modules;
negative fixtures reject feature imports of backend assembly or frontend shell
internals. Documents, Calendar, Courses, Assistant, and Inbox own scoped
test/browser coverage and feature CSS; shared AI and diagnostic UI belongs to
Platform.

Verification: [M21A baseline](../baseline.md). Shared cautions and active
application status remain in the root `handoff.md`.

Item-3 verification on 2026-09-11: `make test-module MODULE=documents` passed 26
backend and 26 frontend host/contract tests. `make test` passed 228 backend and
107 frontend tests plus boundary, catalog-agreement/drift, and data-safety gates;
`make lint` and full/module-mode production frontend builds passed. The focused
stack started beside the owner stack and exposed only Platform/Documents routes
on its isolated ports; temporary containers and test/build volumes were removed.

M21C final verification on 2026-09-24: the focused command passed 34 backend,
29 frontend, and 2 browser tests in 37.24 seconds outer wall time. It uses the
real dependency-closed host, scoped database/filesystem fixtures, a validated
test-only provider, and an isolated browser stack with only Documents private
storage. `make test` passed 228 backend and 108 frontend tests; lint, full and
module builds, all 13 browser scenarios, boundary rejection, and coordinated
relocation/recovery passed.

M21D added exact Calendar backend/frontend public-contract allowances, removed
all 20 M21D legacy exceptions, and generalized dependency-closed host selection
to Calendar. Calendar focused tests attach only isolated PostgreSQL; its browser
stack has no private filesystem volume. Full and focused hosts share the real
application factory, shell, Calendar page/routes, and ICS lifecycle binding. A
warm complete focused run passed 104 backend, 53 frontend, and 2 browser tests
in 53.43 seconds outer wall time.

M21F moved all Assistant/Courses AI and diagnostic imports behind Platform
façades, added Platform-owned AI auth and diagnostic-explanation routes, and
made diagnostic recording own its transaction. Settings can manage ChatGPT
authentication without Assistant. The Assistant focused host closes over real
Calendar/Courses providers; Assistant styles/tests are locally owned. No M21F
boundary exception remains.

M21G consolidated the former top-level mail integration package under Inbox,
bound the mailbox Settings UI through Inbox's public entry, scoped its styles
and tests, and added a typed recovery contribution consumed by Platform. The
focused Inbox host uses real local API/storage with fake IMAP and includes the
shared Settings page for the contributed panel. Both backend and frontend
legacy exception lists are now empty.

M21G verification on 2026-10-01 passed 64 backend, 47 frontend, and one browser
test in the focused command; 254 backend and 122 frontend tests in the full
suite; all 19 full browser/accessibility scenarios; lint; full and focused
builds; coordinated relocation/restore; focused Docker health; and diff
hygiene.

Next step: no milestone is active. M21H is next after explicit owner selection.
M22 remains inactive until M21I is complete.
