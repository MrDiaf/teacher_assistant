# Teacher Assistant development handoff

Updated: 2026-09-08

## Start here

Read, in order:

1. `AGENTS.md`
2. `instructions.md`
3. `handoff.md`
4. The owner-selected milestone
5. `docs/modules/README.md`, the selected owner README/handoff, and only the
   public contracts of relevant dependencies
6. The relevant implementation and tests

Run `git status --short` before editing. Preserve owner work and private data.
Do not commit, push, merge, rebase, delete branches, or discard changes unless
explicitly requested.

## Current state

- M1-M21, the post-M7 linked proposal batches, and the recorded post-M13
  Assistant refinements are complete.
- M21A is implemented in the current uncommitted worktree: ownership/module
  documentation, exact dependency rules, backend/frontend boundary checks,
  invalid fixtures, and a measured verification baseline.
- No feature code, schema, storage identity, private data, or visible design was
  changed by M21A. No M21B or M22 work was started.
- The M21A pre-refactor baseline revision is `dcada0a` (`refactoring immense`).
- The observed migration head is `20260908_0021 (head)`.
- The installation identity remains `teacher_assistant`, with its established
  PostgreSQL, Codex-auth, integration-credential, course-content, mail, and
  document storage identities.
- `.openai/hosting.json` is absent; this remains a self-hosted Docker app.

The authoritative milestone state is in `instructions.md`. Module ownership,
contracts, paths, local work state, and commands are now indexed at
[`docs/modules/README.md`](docs/modules/README.md). Do not reintroduce their
history into this root handoff.

## M21A result

- Every frontend/backend feature, table, storage root, migration content area,
  test area, lifecycle hook, global CSS family, recovery script, and placeholder
  has a Platform or feature owner.
- The intended graph is acyclic: Assistant depends on Courses/Calendar/Platform;
  Courses on Calendar/Platform; Calendar, Inbox, and Documents on Platform.
- Required typed contracts document bounded inputs/outputs, errors, permission
  authority, and transaction ownership without exposing ORM entities,
  repositories, raw sessions, credentials, or physical paths.
- `architecture/module-boundaries.json` records 63 exact backend and 21 exact
  frontend legacy imports. Each has an M21B-M21G removal owner; there are no
  wildcard ignores.
- `make check-boundaries` uses Python AST and the installed TypeScript compiler,
  validates the dependency graph, rejects new/stale violations, and confirms
  deliberately invalid backend/frontend fixtures fail.
- `make test` now depends on the boundary check.
- Root history was reduced; completed feature evidence remains in milestone
  files and local module handoffs.

## Verification

The complete method, commands, timing split, and known failures are in
[`docs/modules/baseline.md`](docs/modules/baseline.md). Pre-refactor results:

```text
Cold no-cache backend+frontend build: 62.24s
Warm cached build: 1.77s
Synthetic DB ready: 3.03s; migration setup: 2.35s
Backend: 167 passed (54.28s cold / 56.52s warm runner)
Frontend: 72 passed (5.39s cold / 5.42s warm runner)
Documents representative backend: 8 passed
Documents representative frontend: 2 passed
E2E/accessibility: 12 passed
Lint: passed
Frontend production build: passed
Data-safety checks: passed
Relocation/backup/restore drill: passed with exact hashes
Isolated DB/backend/frontend startup and health: passed
```

Final M21A worktree verification passed the boundary gate, full backend and
frontend tests, lint, production build, running-stack health, link/JSON checks,
and diff hygiene. The same session's isolated E2E and recovery baselines passed.

## Shared cautions

- M21B-M21I remain separate milestones. Module registration, public code entry
  points, scoped feature CSS, focused `dev-module`/`test-module` commands, and
  Settings module controls do not exist yet.
- M22-M24 remain unimplemented: Documents has no editor, compilation, preview,
  or Codex compilation advice.
- The exact boundary manifest is a burn-down list. Remove entries as owning
  milestones migrate them; never broaden an exception to accommodate new code.
- Assistant confirmation currently relies on one shared SQLAlchemy transaction
  for proposal/job/action and Calendar changes. Course-calendar links also use
  direct Calendar access. Preserve atomicity via the documented coordinator.
- `backend/tests/conftest.py`, the combined E2E file, global `styles.css`, and
  application lifecycle/recovery assembly remain intentionally coupled debt.
- `alembic check` reports deliberately retained retired integration tables and
  four known enum/VARCHAR length differences. It reports no Documents drift.
- A real mailbox-provider check was not run; local fakes cover TLS/read-only,
  authentication, parsing, sync, and failure behavior without credentials.
- Read-only preflight previously found another populated legacy database-volume
  candidate. Never merge, adopt, or delete it implicitly.
- Clean restore excludes renewable Codex and mailbox credentials. Reauthenticate
  or reconnect on a clean target.
- Runtime Codex, mail, course content, Documents source, diagnostics, and
  browser-storage safety rules remain governed by `AGENTS.md` and
  `instructions.md`.
- Automatic LMS imports, assignments, grades, outbound mail, Study Plan, and
  multi-user functionality remain out of scope.

## Exact next step

M21A is complete; stop here. M21B requires explicit owner selection. Its first
subtask is the typed common module
registration/dependency contract and composition validation; it must use the
M21A inventory and tighten the corresponding exact exceptions.

Recommended next prompt:

```text
Select M21B and implement its first incomplete subtask: the typed common module
registration and dependency contract. Preserve behavior and private data, use
the M21A ownership map, remove only verified M21B boundary exceptions, and do
not start M21C or M22.
```
