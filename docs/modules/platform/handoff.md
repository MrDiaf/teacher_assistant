# Platform handoff

Current state: M21B is active and its first four subtasks are complete. Matching
strict Python and TypeScript catalogs define stable module/page order,
dependency capabilities, route identities, settings contributions, and
lifecycle identities without import paths or executable names.

`make check-module-contract` verifies frontend/backend catalog agreement,
identity and dependency agreement with `architecture/module-boundaries.json`,
and rejection of deliberate drift. Typed tests reject duplicate IDs/orders,
unknown modules, missing capabilities, cycles, duplicate route contributions,
and extra executable-looking fields. `make test` runs this gate.

Every current owner now exposes an explicit page/router entry. Platform's
frontend catalog binds page IDs to statically imported components; `App.tsx`
and `AppShell.tsx` render and navigate those registrations. Platform's backend
catalog binds route IDs to statically imported FastAPI routers; `main.py`
includes them through one validated assembly function. Code-entry validation
rejects missing/unknown/duplicate contributions and duplicate HTTP method/path
pairs. Test-only entries can be assembled and mounted without changing shell
rendering or importing unrelated production modules.

Each public backend entry now binds its declared lifecycle identities to
explicit startup functions. Platform runs only the supplied entries in stable
effect order, retains successful cleanup callbacks, and unwinds them in reverse
after normal shutdown or a later startup failure. Every cleanup has a
five-second hard bound; startup cleanup preserves the original startup error.
The full app supplies every registered entry, initializes existing private roots
before starting the ICS/mail schedulers, and retains the existing Assistant and
Codex shutdown behavior. Selective test assembly starts no unselected hook.

Feature code now imports the existing icon/modal, API error, browser persistence,
and model-selection primitives through narrow Platform façades. Persistence no
longer imports Calendar or Courses types, the version-1 storage envelope is
unchanged, and focused tests cover legacy state restoration. Root tokens,
shell/navigation, accessibility, responsive-shell, and placeholder styling now
have a Platform-owned stylesheet; feature CSS remains in the legacy stylesheet.
Generic enum serialization moved out of Calendar and into Platform database
infrastructure. Thin backend Platform façades publish the existing AI/runtime
and diagnostic interfaces for M21F to restructure behind. No M21B boundary
exception remains; focused commands, scoped
feature CSS, and deeper M21F AI/diagnostic separation are still unimplemented.

Verification: [M21A baseline](../baseline.md). Shared cautions and active
application status remain in the root `handoff.md`.

Current verification: `make test` passed 191 backend and 90 frontend tests plus
boundary, catalog-drift, and data-safety gates. `make lint`, the frontend
production build, and all 12 E2E/accessibility tests passed.

Next step: continue M21B with its fifth checklist item: add composition,
missing-dependency, duplicate-registration, and lifecycle tests, then tighten
the corresponding M21A boundary allowances. Do not start the final M21B
documentation item or M21C automatically.
