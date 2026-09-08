# Documents module

## Ownership and current locations

Documents owns the implemented M21 project/tag metadata, source creation and
validation, source downloads, deletion compensation, API/UI/styles, and tests.
Current code is `backend/app/documents/`, `frontend/src/features/documents/`,
`backend/tests/test_documents.py`, its frontend test, and Documents portions of
data-archive/E2E tests. Tables are `document_projects`, `document_tags`, and
`document_project_tags` from migration 0021. Source lives under the configurable
private document root.

Editing, compilation, preview, and Codex compilation advice are not implemented
or part of this boundary.

## Required public contracts

- A module entry contributes current routers/page and later focused-test setup.
- A recovery contribution lets Platform coordinate a checksummed source archive
  with PostgreSQL state and old-format compatibility. It returns bounded archive
  metadata, never a browser-visible physical path.
- Documents currently has no cross-feature business consumer and therefore no
  generic project repository/query contract.

Documents owns project/tag validation and document storage errors. Services own
commits. Project creation rolls back DB and created storage on failure; deletion
quarantines the exact UUID tree, restores it after transaction failure, and
purges only after commit. Platform recovery remains the cross-owner coordinator.

## Dependencies and migration debt

Documents depends only on Platform configuration/errors/database, UI primitives,
and coordinated recovery. `main.py` imports its route/storage internals until
M21B. Documents selectors remain global until the M21C pilot. There are no
current Documents-to-feature import exceptions.

## Current commands

```bash
make dev
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/test_documents.py
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/documents/DocumentsPage.test.tsx
make test
make e2e
make data-relocation-test
```

The selected tests still use full-app fixtures. M21C builds the real isolated
module host. See measured limitations in the [M21A baseline](../baseline.md).
