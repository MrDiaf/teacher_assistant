# Documents module

## Ownership and current locations

Documents owns the implemented M21 project/tag metadata, source creation and
validation, source downloads, deletion compensation, API/UI/styles, and tests.
Current code is `backend/app/documents/`, including its owned application and
storage errors, and `frontend/src/features/documents/`, including its scoped
`styles.css`. Tests currently include `backend/tests/test_documents.py`, the
colocated frontend test, and Documents portions of data-archive/E2E tests.
Tables are `document_projects`, `document_tags`, and `document_project_tags`
from migration 0021. Source lives under the configurable private document root.

Editing, compilation, preview, and Codex compilation advice are not implemented
or part of this boundary.

## Required public contracts

- `backend/app/documents/entry.py` and
  `frontend/src/features/documents/entry.ts` contribute the current router and
  page through Platform composition. The frontend entry also loads the
  Documents-owned stylesheet; focused-test setup remains pending.
- `backend/app/documents/recovery.py`, re-exported by the public backend entry,
  contributes the established `document_files`, `document-projects.tar.gz`, and
  `document_projects` identities, format-3 introduction, and archive limits to
  Platform. The typed declaration contains no live path, database/session,
  repository, restore order, or executable callback.
- Documents currently has no cross-feature business consumer and therefore no
  generic project repository/query contract.

Documents owns project/tag validation and document storage errors. Services own
commits. Project creation rolls back DB and created storage on failure; deletion
quarantines the exact UUID tree, restores it after transaction failure, and
purges only after commit. Platform recovery consumes the Documents contribution
while retaining cross-owner quiescence, checksums, format-2 handling, restore
ordering, and rollback coordination.

## Dependencies and migration debt

Documents depends only on Platform configuration/error bases/database, UI
primitives, and coordinated recovery. `main.py` consumes the router and
private-root setup through the public entry. Documents application/storage
errors and feature selectors are now owned inside the module; its delete dialog
no longer consumes Courses-specific selectors. There are no current
Documents-to-feature import exceptions.

## Current commands

```bash
make dev
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/test_documents.py
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/test_data_archive.py
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/documents/DocumentsPage.test.tsx
make test
make e2e
make data-relocation-test
```

The selected tests still use full-app fixtures. M21C builds the real isolated
module host. See measured limitations in the [M21A baseline](../baseline.md).
