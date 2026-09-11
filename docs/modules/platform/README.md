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
| Frontend pages | `frontend/src/platform/entry.ts` for Platform pages and `frontend/src/features/<owner>/entry.ts` for feature pages | `frontendCatalog.ts` statically imports every entry, `assembleFrontendPages` validates it, and `App.tsx` passes `registeredPages` to `RegisteredApplication` |
| Backend routes and lifecycle hooks | `backend/app/platform/entry.py` and `backend/app/<owner>/entry.py` | `backend_catalog.py` statically imports every entry, `assemble_backend_modules` validates it, and `app/main.py` includes routers and runs `backend_module_lifespan` |
| Test-only page/router assembly | A synthetic validated catalog plus an explicit tuple of test entries | Call `assembleFrontendPages` or `assemble_backend_modules` directly; do not mutate the production catalogs or global registered entry sets |

The Settings-panel IDs in the metadata currently reserve and validate identity
and order only. The existing mailbox panel remains directly hosted by Settings;
M21G owns its code contribution and M21H owns module switches. Do not treat
`enabled_by_default` as a runtime module switch before M21H.

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
3. Add the public entry to the corresponding static tuple in
   `frontendCatalog.ts` and/or `backend_catalog.py`. Do not add dynamic discovery,
   import strings, a service locator, or business logic to either catalog.
4. For a lifecycle hook, bind the declared ID to an async startup callback with
   a unique global order. Startup may return an idempotent async cleanup; use
   `background_task_lifecycle` for a cooperative scheduler. Cleanups run in
   reverse successful-start order and each has a positive, finite timeout
   (five seconds by default). Private roots must start before jobs that use them.
5. Update `architecture/module-boundaries.json` with ownership, declared
   dependencies, and the exact public-entry path. Do not add a broad exception
   or allow a business feature to import Platform assembly internals.
6. Add metadata, missing/unknown/duplicate binding, page/router, and lifecycle
   tests as applicable. Run `make check-module-contract`,
   `make check-boundaries`, and the relevant full regression commands.

Production assembly intentionally requires an entry for every registration and
keeps every current module enabled. Selective tests instead pass only a matching
synthetic catalog and explicit entries, so unrelated private storage and
schedulers are never started.

## Shared Platform entry points

- Frontend feature code may use `platform/ui`, `platform/api`,
  `platform/persistence`, `platform/ai`, and
  `platform/modules/frontendContract` as permitted by the boundary manifest.
  `platform/shell` and `platform/entry` are root-composition surfaces, not
  business-feature imports. Persistence retains the exact
  `teacher-assistant.ui-state.v1` key and version-1 bounded schema.
- `app.platform.modules.backend_contract` publishes route, lifecycle, and module
  code-entry types plus the assembly/lifespan functions.
- `app.platform.recovery` publishes the bounded storage-recovery declaration.
  Documents supplies its stable archive identities and limits through its public
  entry; Platform retains coordinated archive/restore behavior and no live path,
  session, repository, or executable callback appears in the declaration.
- `app.platform.ai` publishes existing model listing/validation,
  authentication, Codex execution, and bounded private-workspace interfaces.
  M21F may restructure their implementations behind this surface.
- `app.platform.diagnostics` publishes safe schemas, redaction helpers, and the
  diagnostic service interface. Credentials and raw provider output remain
  forbidden; M21F owns removal of its remaining persistence coupling.
- Generic database enum serialization lives in `app.database.types` as Platform
  infrastructure. Configuration, errors, database sessions, and models remain
  infrastructure rather than unrestricted feature service APIs.

The Documents recovery contribution is implemented; equivalent ownership for
other private roots remains with their later module milestones. The explicit
cross-module transaction coordinator also remains later-milestone work. Neither
interface may expose an unrestricted session, physical private path, credential,
or feature repository.

Platform owns configuration/database availability and safe diagnostic errors.
Feature permissions stay with the feature owner. Database sessions remain
internal infrastructure. Migrations always register every model regardless of
which UI/test module is selected.

## Dependencies and migration debt

The business graph gives Platform no feature dependency. Its composition layer
may import only the exact module `entry.py`/`entry.ts` files declared in the
boundary manifest; that root wiring is not permission for other Platform code
to reach feature internals. Feature code consumes the Platform UI, persistence,
API, and model-selection façades; Settings still imports Inbox internals.
AI/diagnostic deeper separation belongs to M21F; mail Settings separation belongs
to M21G. Feature selectors remain deliberately mixed in the legacy stylesheet
until their owner milestones extract them.

## Current commands

```bash
make dev
make down
make restart
make logs
make check-boundaries
make check-module-contract
make test
make e2e
make lint
make migrate
make data-relocation-test
```

No focused `dev-module`/`test-module` command exists yet; M21C implements it.
See the [M21A baseline](../baseline.md).
