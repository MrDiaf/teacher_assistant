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

## Required public contracts

The first five contracts below have concrete entry surfaces; M21F restructures
the AI/diagnostic implementations behind them and later milestones establish
the remaining entries:

- A typed, metadata-only module registration contract for stable IDs,
  navigation/pages, router identities, declared dependency capabilities,
  settings contributions, and lifecycle identities lives in
  `backend/app/platform/modules/` and `frontend/src/platform/modules/`. Strict
  parsers reject missing/unknown fields, duplicate IDs/orders, missing modules
  or capabilities, and dependency cycles. `frontendCatalog.ts` and
  `backend_catalog.py` attach explicitly imported public entries and validate
  that their page/router code matches the metadata; catalog/browser input
  cannot name code to import or execute.
- Backend public entries bind lifecycle identities to explicit async startup
  functions. Platform starts only the supplied entry set in stable effect order,
  records successful cleanup callbacks, unwinds them in reverse after startup
  failure, and gives each shutdown callback a five-second hard bound. The full
  app supplies all registered entries; selective tests may supply only their
  chosen entries without opening unrelated private roots or schedulers.
- Shared UI entry points for the existing icon, modal, shell, persistence, API
  error, model selector, and styling/token needs actually used by modules live
  under `frontend/src/platform/`. Persistence retains the version-1 storage key
  and owns its bounded Calendar-view/Course-tab value types without importing a
  feature. Generic database enum serialization lives in Platform infrastructure.
- `backend/app/platform/ai.py` publishes the existing model
  listing/validation, authentication, Codex execution, and bounded private
  workspace interfaces without moving their implementation. They do not query
  feature data; M21F restructures providers behind this entry point.
- `backend/app/platform/diagnostics.py` publishes the existing safe schemas,
  redaction helpers, and diagnostic service interface. Credentials and raw
  provider output remain forbidden; M21F removes its remaining persistence
  coupling behind this entry point.
- A recovery coordinator consumes typed module contributions and owns quiescence,
  manifest/checksum validation, rollback, and old-format compatibility.
- An application transaction coordinator accepts specific cross-module use
  cases. It never exposes an unrestricted session as a module public API.

Platform owns configuration/database availability and safe diagnostic errors.
Feature permissions stay with the feature owner. Database sessions remain
internal infrastructure. Migrations always register every model regardless of
which UI/test module is selected.

## Dependencies and migration debt

The business graph gives Platform no feature dependency. Composition imports
only the exact module `entry.py`/`entry.ts` files declared in the boundary
manifest. `App.tsx` renders registered pages, while `main.py` includes validated
registered routers and runs their lifecycle contributions. Feature code consumes
the Platform UI, persistence, API, and model-selection façades; Settings still
imports Inbox internals. AI/diagnostic deeper separation belongs to M21F; mail
Settings separation belongs to M21G. Feature selectors remain deliberately mixed
in the legacy stylesheet until their owner milestones extract them.

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
