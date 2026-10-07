# Platform and shell

## Ownership and current locations

Platform owns React/FastAPI composition, sidebar/navigation/placeholders,
Settings host, common UI primitives, browser preference storage, configuration,
safe application errors, database engine/session creation, centrally ordered
migrations, coordinated backup/restore/relocation, shared AI authentication and
model allowlisting, Codex adapter/workspace lifecycle, and sanitized diagnostics.

Current paths include `frontend/src/{App,main,styles}.tsx`/`styles.css`,
`frontend/src/platform/`, `components/`, `hooks/`, `persistence/`,
`features/{ai,settings}/`, `backend/app/platform/`,
`backend/app/{main,core,database,ai,codex_runtime,diagnostics,maintenance}/`,
`backend/alembic/`, root Compose/Make files, and `scripts/`. Dashboard and Study
Plan remain shell placeholders. Platform owns no feature business tables; its
diagnostic tables are `diagnostic_errors` and `diagnostic_audit_records`.

## Implemented composition extension points

Composition is explicit and static. Metadata describes an extension, a public
entry binds that metadata to code, and a Platform-owned catalog assembles the
known entries. Neither catalog data nor browser input is interpreted as an
import path, component name, router name, or executable.

| Concern | Declaration or public entry | Platform assembly consumer |
| --- | --- | --- |
| Shared identities, order, dependencies, capabilities, routes, pages, Settings panels, and lifecycle IDs | Mirrored `backend/app/platform/modules/catalog.json` and `frontend/src/platform/modules/catalog.json` | Strict `contract.py`/`contract.ts` parsers; `make check-module-contract` also compares both files with the ownership manifest |
| Frontend pages and Settings panels | `frontend/src/platform/entry.ts` for Platform pages and `frontend/src/features/<owner>/entry.ts` for feature pages/panels | `frontendCatalog.ts` statically imports every production entry; `App.tsx` passes all pages and panels to `RegisteredApplication`, while `ModuleHost.tsx` passes dependency-selected contributions to the same shell |
| Backend routes and lifecycle hooks | `backend/app/platform/entry.py` and `backend/app/<owner>/entry.py` | `backend_catalog.py` statically imports every production entry; the shared `app.platform.application` factory hosts either the full set from `app/main.py` or a dependency-selected set from `app/module_host.py` |
| Test-only page/router assembly | A synthetic validated catalog plus an explicit tuple of test entries | Call `assembleFrontendPages` or `assemble_backend_modules` directly; do not mutate the production catalogs or global registered entry sets |

Settings-panel metadata is bound to explicit code contributions with the same
missing, unknown, duplicate-ID, and duplicate-order validation as pages. The
shared Settings page renders only the contributions supplied by composition;
Inbox owns the mailbox panel and Platform owns the AI panel. M21H owns module
switches, so do not treat `enabled_by_default` as a runtime switch before then.

### Adding an entry in an owner-selected milestone

1. Add the same metadata registration to both catalog JSON files. Keep IDs
   lowercase kebab-case and globally unique, give module/page/Settings orders
   unique integers, and declare only capabilities actually provided and
   dependencies actually consumed. Update the closed `ModuleId`/`PageId` types
   when an explicitly approved module or page is added.
2. Add or update the owner public `entry.ts` and/or `entry.py`. A frontend page
   binds its metadata ID to an explicitly imported React component and icon. A
   backend route binds its metadata ID to an explicitly imported `APIRouter`,
   normally under `/api/v1`.
3. Bind any Settings panel as an explicit `settingsPanels` contribution in its
   owner's frontend entry. Keep all panel-specific state, API calls, and error
   handling in that owner; the shared Settings page only renders contributions.
4. Add the public entry to the corresponding static tuple in
   `frontendCatalog.ts` and/or `backend_catalog.py`. Do not add dynamic discovery,
   import strings, a service locator, or business logic to either catalog.
5. For a lifecycle hook, bind the declared ID to an async startup callback with
   a unique global order. Startup may return an idempotent async cleanup; use
   `background_task_lifecycle` for a cooperative scheduler. Cleanups run in
   reverse successful-start order and each has a positive, finite timeout
   (five seconds by default). Private roots must start before jobs that use them.
6. Update `architecture/module-boundaries.json` with ownership, declared
   dependencies, and the exact public-entry path. Do not add a broad exception
   or allow a business feature to import Platform assembly internals.
7. Add metadata, missing/unknown/duplicate binding, page/panel/router, and lifecycle
   tests as applicable. Run `make check-module-contract`,
   `make check-boundaries`, and the relevant full regression commands.

Production assembly intentionally requires an entry for every registration and
keeps every current module enabled. The focused host accepts only an explicit
allowlisted module ID, closes its declared dependency set, and assembles only
matching real entries. `documents` hosts Platform plus Documents; `calendar`
hosts Platform plus Calendar; `courses` adds Courses; and `assistant` adds
Assistant over its real Calendar/Courses providers. `inbox` hosts Inbox plus
the Platform Settings page needed to render its mailbox contribution. Other
focused UIs present only the selected page.

The root `compose.module.yml` override retains the normal images/source mounts
but selects the focused host through configuration. Its distinct Compose project,
ports, database, and named private-data volumes prevent access to the owner's
running installation. The UI uses `RegisteredApplication`, not a copied shell;
test-level fetch fakes remain confined to tests and ordinary startup has no fake
route or response provider.

## Shared Platform entry points

- Frontend feature code may use `platform/ui`, `platform/api`,
  `platform/persistence`, `platform/ai`, `platform/diagnostics`, and
  `platform/modules/frontendContract` as permitted by the boundary manifest.
  `platform/shell` and `platform/entry` are root-composition surfaces, not
  business-feature imports. Persistence retains the exact
  `teacher-assistant.ui-state.v1` key and version-1 bounded schema.
- `app.platform.modules.backend_contract` publishes route, lifecycle, and module
  code-entry types plus the assembly/lifespan functions.
- `app.platform.recovery` publishes the bounded storage-recovery declaration.
  Documents, Courses, and Inbox supply stable archive identities and limits
  through their public entries; Platform retains coordinated archive/restore
  behavior and no live path, credential, session, repository, or executable
  callback appears in a declaration.
- `app.platform.ai` publishes model listing/validation, authentication, Codex
  execution, and bounded private-workspace interfaces. Platform-owned
  `/api/v1/ai/auth*` routes and the Settings panel use the same auth manager as
  the compatible Assistant sign-in routes.
- `app.platform.diagnostics` publishes safe schemas, redaction helpers, and the
  diagnostic service interface. `record_diagnostic_error` accepts no feature
  session and returns a bounded value from its own transaction. Credentials and
  raw provider output remain forbidden. Frontend consumers use the matching
  `platform/diagnostics` contribution.
- Generic database enum serialization lives in `app.database.types` as Platform
  infrastructure. Configuration, errors, database sessions, and models remain
  infrastructure rather than unrestricted feature service APIs.

The Documents, Courses, and Inbox recovery contributions are implemented.
Calendar's restricted Assistant port binds internally to the coordinator's transaction
without exposing a session, repository, raw SQL, physical path, or credential.

Platform owns configuration/database availability and safe diagnostic errors.
Feature permissions stay with the feature owner. Database sessions remain
internal infrastructure. Migrations always register every model regardless of
which UI/test module is selected.

## Dependencies and migration debt

The business graph gives Platform no feature dependency. Its composition layer
may import only the exact module `entry.py`/`entry.ts` files declared in the
boundary manifest; that root wiring is not permission for other Platform code
to reach feature internals. Feature code consumes the Platform UI, persistence,
API, and model-selection façades. Settings owns only the generic contribution
host and imports no Inbox internals. Inbox, Assistant, Calendar, Courses, and
Documents styles are feature-owned.

## Current commands

```bash
make dev
make down
make restart
make logs
make check-boundaries
make check-module-contract
make test
make dev-module MODULE=assistant
make test-module MODULE=assistant
make dev-module MODULE=calendar
make test-module MODULE=calendar
make dev-module MODULE=courses
make test-module MODULE=courses
make dev-module MODULE=documents
make test-module MODULE=documents
make dev-module MODULE=inbox
make test-module MODULE=inbox
make logs-module MODULE=inbox
make down-module MODULE=inbox
make logs-module MODULE=documents
make down-module MODULE=documents
make e2e
make lint
make migrate
make data-relocation-test
```

Only `assistant`, `calendar`, `courses`, `documents`, and `inbox` are currently allowlisted; unknown and multiple
IDs fail before Compose starts. The development defaults are UI `15173` and API `18000` and may
be overridden with `MODULE_FRONTEND_PORT`/`MODULE_BACKEND_PORT`. The focused
test command verifies dependency closure, real entries, routes, lifecycle
selection, shell rendering, and invalid-ID rejection. Calendar adds scoped API,
provider/consumer, and independently seeded browser coverage without private
mounts; Assistant adds mocked-Codex runtime/contract coverage plus a bounded
fixture browser scenario; Documents adds CRUD/storage, contract-checked fake
behavior, and real/fake browser scenarios with only isolated Documents storage;
Inbox adds fake-IMAP API/storage, contributed Settings, and a browser scenario
with only isolated credential and attachment storage.
See the [M21A baseline](../baseline.md).
