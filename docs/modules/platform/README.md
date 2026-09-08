# Platform and shell

## Ownership and current locations

Platform owns React/FastAPI composition, sidebar/navigation/placeholders,
Settings host, common UI primitives, browser preference storage, configuration,
safe application errors, database engine/session creation, centrally ordered
migrations, coordinated backup/restore/relocation, shared AI authentication and
model allowlisting, Codex adapter/workspace lifecycle, and sanitized diagnostics.

Current paths include `frontend/src/{App,main,styles}.tsx`/`styles.css`,
`components/`, `hooks/`, `persistence/`, `features/{ai,settings}/`,
`backend/app/{main,core,database,ai,codex_runtime,diagnostics,maintenance}/`,
`backend/alembic/`, root Compose/Make files, and `scripts/`. Dashboard and Study
Plan remain shell placeholders. Platform owns no feature business tables; its
diagnostic tables are `diagnostic_errors` and `diagnostic_audit_records`.

## Required public contracts

These become concrete in M21B/M21F:

- A typed module registration contract for stable ID, navigation/page, routers,
  declared dependencies, settings/recovery contributions, and lifecycle hooks.
- Shared UI entry points for the existing icon, modal, shell, persistence, API
  error, and styling/token needs actually used by modules.
- AI ports for model listing/validation, authentication, Codex execution, and
  bounded private workspace lifecycle. They do not query feature data.
- Diagnostic ports accept sanitized bounded error records and return typed safe
  IDs/explanations; credentials and raw provider output are forbidden.
- A recovery coordinator consumes typed module contributions and owns quiescence,
  manifest/checksum validation, rollback, and old-format compatibility.
- An application transaction coordinator accepts specific cross-module use
  cases. It never exposes an unrestricted session as a module public API.

Platform owns configuration/database availability and safe diagnostic errors.
Feature permissions stay with the feature owner. Database sessions remain
internal infrastructure. Migrations always register every model regardless of
which UI/test module is selected.

## Dependencies and migration debt

The business graph gives Platform no feature dependency. Composition may import
public module entries only. Current `App.tsx`, `main.py`, and lifecycle code reach
feature internals directly; exact exceptions are removed in M21B. `uiState`
imports feature types and Settings imports Inbox internals. AI/diagnostic deeper
separation belongs to M21F; mail Settings separation belongs to M21G. The global
stylesheet remains deliberately mixed until feature milestones extract it.

## Current commands

```bash
make dev
make down
make restart
make logs
make check-boundaries
make test
make e2e
make lint
make migrate
make data-relocation-test
```

No focused `dev-module`/`test-module` command exists yet; M21C implements it.
See the [M21A baseline](../baseline.md).
