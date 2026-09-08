# M21A verification and timing baseline

Measured 2026-09-08 in Europe/Oslo against pre-refactor revision `dcada0a`
(`refactoring immense`). M21A adds only documentation and architecture checks;
application source, schema, storage identity, and behavior were unchanged when
these measurements were taken.

## Environment and method

- Linux `7.0.0-28-generic` x86_64; 12 Docker CPUs; 49,323,249,664 bytes memory.
- Docker Engine 29.1.3; Docker Compose 2.40.3.
- PostgreSQL 16.4 image; Alembic `20260908_0021 (head)`.
- `/usr/bin/time` reports wall time around each Docker command. Test-runner time
  is reported separately where available.
- “Cold build” means `--no-cache` with base images already local; it is not a
  network-pull benchmark. “Warm build” reuses BuildKit layers. “Cold/warm test”
  means first/second fresh test container against the same isolated synthetic
  test stack; OS/Docker caches were not flushed.
- No owner database, source tree, mail, credential, or Codex credential was
  copied into a test environment.

## Setup and execution measurements

| Measurement | Result | Outer wall time |
| --- | --- | ---: |
| Backend + frontend image build, cold `--no-cache` | passed | 62.24s |
| Same image build, warm cached | passed | 1.77s |
| Synthetic PostgreSQL create + healthy | passed | 3.03s |
| Alembic empty-database upgrade to head | passed | 2.35s |
| Backend full, cold | 167 passed in 54.28s | 58.35s |
| Backend full, warm | 167 passed in 56.52s | 60.60s |
| Frontend full, cold | 72 passed in 5.39s | 6.39s |
| Frontend full, warm | 72 passed in 5.42s | 6.48s |
| Documents backend representative, cold | 8 passed in 2.47s | 6.32s |
| Documents backend representative, warm | 8 passed in 3.00s | 6.87s |
| Documents frontend representative, cold | 2 passed in 1.76s | 2.74s |
| Documents frontend representative, warm | 2 passed in 1.78s | 2.73s |

The Documents commands select only the existing Documents test files, but the
backend still imports the full app fixture and resets all tables/storage. These
are representative timings, not an isolated module claim; M21C supplies the
module host and scoped fixtures.

## Functional baseline

| Command/check | Result | Outer wall time |
| --- | --- | ---: |
| `make e2e` | 12 Playwright/accessibility tests passed (26.9s runner) | 41.26s |
| `make lint` | Ruff, frontend TypeScript/Prettier, E2E TypeScript/Prettier passed | 12.24s |
| Frontend `npm run build` in Docker | 67 modules; Vite build 1.11s | 6.00s |
| `make data-safety-test` | shell and isolated Compose checks passed | 0.17s |
| `make data-relocation-test` | synthetic backup/restore/relocation and exact hashes passed | 114.09s |
| Isolated full-stack `up --build -d --wait frontend` | DB/backend/frontend healthy; `/health` and HTML fetched | 11.57s |

After implementation, `make check-boundaries` also passed both production
scans and demonstrated that the backend and frontend invalid-import fixtures
are rejected. It is intentionally not included in the pre-refactor timing.

## Reproduction commands

The full command is `make test`; it now includes boundary checks, backend and
frontend suites, and data-safety checks. The measured execution-only commands
used the isolated `teacher-assistant-m21a-baseline` Compose project:

```bash
docker compose -p teacher-assistant-m21a-baseline -f compose.yml -f compose.test.yml build --no-cache backend frontend
docker compose -p teacher-assistant-m21a-baseline -f compose.yml -f compose.test.yml up -d --wait database
docker compose -p teacher-assistant-m21a-baseline -f compose.yml -f compose.test.yml run --rm backend true
docker compose -p teacher-assistant-m21a-baseline -f compose.yml -f compose.test.yml run --rm --entrypoint pytest backend -q
docker compose -p teacher-assistant-m21a-baseline -f compose.yml -f compose.test.yml run --rm --no-deps frontend npm run test
docker compose -p teacher-assistant-m21a-baseline -f compose.yml -f compose.test.yml run --rm --entrypoint pytest backend -q tests/test_documents.py
docker compose -p teacher-assistant-m21a-baseline -f compose.yml -f compose.test.yml run --rm --no-deps frontend npm run test -- src/features/documents/DocumentsPage.test.tsx
```

Always tear down a measurement project with `down -v --remove-orphans`.

## Known failures and warnings

- `alembic check` exits 255 on this installation because it sees the deliberately
  retained, retired local `integration_connections` and
  `integration_oauth_states` tables plus four known enum/VARCHAR length diffs.
  It reports no Documents drift. No schema was changed to manufacture a pass.
- The cold frontend `npm ci` reported three dependency audit findings (one
  moderate, two high). The required pinned build, tests, lint, and E2E passed;
  dependency updates are outside M21A.
- Compose reports that Bake is configured but `buildx` is not installed. The
  standard Docker builds still completed successfully.
- Timing noise is visible: the second backend run was slower than the first.
  These values are observations, not a performance guarantee.
