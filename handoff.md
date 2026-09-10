# Teacher Assistant development handoff

Updated: 2026-09-09

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
- M21A is complete at revision `d826ac1` (`m21a is done`).
- M21B is active. Its first four checklist items—the typed common module
  contract, explicit frontend-page/backend-router assembly, registered backend
  lifecycle hooks, and shared UI/platform entry points with compatible
  navigation state—are implemented in the current uncommitted worktree.
- No feature behavior, schema, storage identity, private data, or visible design
  was changed. M21C and M22 were not started.
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

## M21B current result

- Matching metadata catalogs describe the six architecture owners and all eight
  current pages in stable order, including route, settings-panel, lifecycle,
  dependency, and capability identities.
- Strict Python and TypeScript contracts reject malformed schemas, duplicate
  registrations/contributions/orders, missing dependencies/capabilities, and
  cycles. Unknown lookup input returns no registration and cannot name code.
- `make check-module-contract` detects frontend/backend or ownership/dependency
  drift and is now part of `make test`.
- Every current module exposes an explicit page/router entry. Static Platform
  catalogs bind those entries to validated metadata; no runtime value names a
  component, router, import, or executable.
- `App.tsx`/`AppShell.tsx` render the ordered page registrations, while
  `app/main.py` includes validated registered routers. Test fixtures prove a
  page or router can mount without production assembly changes.
- Public backend entries bind all seven existing private-root, scheduler,
  Assistant-registry, and Codex-auth lifecycle identities. Platform starts only
  hooks from the supplied entries, records successful cleanup callbacks, and
  unwinds them in reverse after normal shutdown or a later startup failure.
- Every cleanup has a five-second hard bound. A failed or timed-out cleanup is
  safely logged without skipping earlier hooks; normal shutdown reports the
  aggregate failure, while startup cleanup preserves the original startup
  exception. Full-app assembly supplies every registered entry in the existing
  effective order: private roots before the two schedulers.
- Feature code now consumes stable Platform façades for the existing icon,
  modal hook, API error parser, browser preferences, and shared model selector.
  Root tokens, reset, shell/navigation, accessibility, and placeholder CSS live
  in Platform styling; feature selectors remain in the legacy stylesheet for
  their scheduled owner milestones.
- Browser persistence owns its bounded Calendar-view and Course-tab value types
  instead of importing feature types. The storage key remains exactly
  `teacher-assistant.ui-state.v1`, version 1, and existing module, Calendar,
  Course, Assistant-sidebar, and draft values restore unchanged.
- Generic database enum-value serialization moved from Calendar to Platform
  database infrastructure without a schema or stored-value change.
- Stable backend Platform façades now publish the existing AI/model-selection,
  private-workspace, redaction, and diagnostic interfaces; M21F still owns
  restructuring their implementation and removing persistence coupling.
- The boundary allowlist now permits only the five exact feature entry paths.
  Removing direct composition and shared-helper imports reduced exact exceptions
  from 63 to 38 backend and from 21 to 7 frontend; no M21B exception remains.
- Current-subtask verification passed `make test` (191 backend and 90 frontend
  tests, boundary/catalog-drift/data-safety gates), the frontend production
  build, `make lint`, and all 12 E2E/accessibility tests.

## Shared cautions

- M21B-M21I remain separate milestones. Metadata registration, public
  page/router entries, catalog-driven assembly, and lifecycle registration now
  exist alongside shared UI/platform façades. Scoped feature CSS, focused
  `dev-module`/`test-module` commands, and Settings module controls do not exist
  yet.
- M22-M24 remain unimplemented: Documents has no editor, compilation, preview,
  or Codex compilation advice.
- The exact boundary manifest is a burn-down list. Remove entries as owning
  milestones migrate them; never broaden an exception to accommodate new code.
- Assistant confirmation currently relies on one shared SQLAlchemy transaction
  for proposal/job/action and Calendar changes. Course-calendar links also use
  direct Calendar access. Preserve atomicity via the documented coordinator.
- `backend/tests/conftest.py`, the combined E2E file, global `styles.css`, and
  recovery assembly remain intentionally coupled debt.
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

M21B is active and its first four checklist items are complete. The exact next
step is its fifth checklist item: add composition, missing-dependency,
duplicate-registration, and lifecycle tests, then tighten the corresponding
M21A boundary allowances.

Recommended next prompt:

```text
Continue M21B with its next incomplete subtask: add composition,
missing-dependency, duplicate-registration, and lifecycle tests, and tighten the
corresponding M21A boundary allowances. Preserve behavior, design, storage IDs,
and private data; do not start the final M21B documentation item, M21C, or M22.
```
