# Documents module

## Ownership and current locations

Documents owns the implemented M21 project/tag metadata, source creation and
validation, source downloads, deletion compensation, API/UI/styles, and tests.
Current code is `backend/app/documents/`, including its owned application and
storage errors, and `frontend/src/features/documents/`, including its scoped
`styles.css`. Tests include `backend/tests/documents/`, the colocated frontend
page and fake-provider contract tests, `e2e/tests/documents.spec.ts`, and
Documents portions of the coordinated data-archive tests.
Tables are `document_projects`, `document_tags`, and `document_project_tags`
from migration 0021. Source lives under the configurable private document root.

Editing, compilation, preview, and Codex compilation advice are not implemented
or part of this boundary.

## Required public contracts

- `backend/app/documents/entry.py` and
  `frontend/src/features/documents/entry.ts` contribute the current router and
  page through Platform composition. The frontend entry also loads the
  Documents-owned stylesheet. The shared focused host selects these real entries
  plus their Platform dependency; it does not define a second Documents UI/API.
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
make dev-module MODULE=documents
make test-module MODULE=documents
make logs-module MODULE=documents
make down-module MODULE=documents
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/test_data_archive.py
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/documents
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/documents
make test
make e2e
make data-relocation-test
```

The focused development host runs on separate default ports (UI `15173`, API
`18000`) and project-scoped PostgreSQL/private-data volumes. `test-module`
combines host/selection contracts with the owned backend, frontend, and browser
scenarios. Unknown or multiple module IDs fail before Compose starts.

## Focused fixture and storage contract

- Backend Documents tests mount the real Platform+Documents application, not a
  copied API. Their closer fixture truncates only `document_project_tags`,
  `document_tags`, and `document_projects`, and assigns a fresh private
  per-test source root. It refuses non-test databases and does not clear another
  owner's storage.
- Focused unit Compose attaches only its isolated PostgreSQL volume and no
  private root. Focused browser Compose attaches its isolated database and only
  the Documents source volume. Centrally ordered migrations still build the
  complete schema; selection does not weaken migration or foreign-key safety.
- The frontend fake provider lives under Documents test support, validates
  methods, paths, payload keys, and response shapes, and rejects undeclared
  requests. The reversible browser fake is route-local. Neither is imported by
  production entries or enabled in ordinary startup.
- The real browser scenario retains project creation, tagging, download,
  filtering, deletion confirmation, keyboard semantics, and accessibility
  coverage against the focused API and private storage.

## M21C measurements and limitations

Measured warm on 2026-09-24, `make test-module MODULE=documents` took 37.24
seconds outer wall time: 34 backend tests in 8.40 seconds, 29 frontend tests in
2.04 seconds, and 2 browser tests in 3.7 seconds. M21A separately measured an
8-test backend file and 2-test frontend file at 6.32-6.87 and 2.73-2.74 seconds
outer wall time. The M21C command adds host contracts and browser startup, so
these figures demonstrate focused selection but are not a direct speedup
comparison.

Only Documents is allowlisted in the focused host. Other module hosts and
module switches remain later milestones. The shared full-suite fixture still
resets all owners outside the Documents subtree. M22 editing and M23-M24
compilation/advice remain unimplemented. See the broader baseline in
[M21A baseline](../baseline.md).
