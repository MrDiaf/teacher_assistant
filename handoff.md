# Teacher Assistant development handoff

Updated: 2026-09-30

## Start here

Read, in order:

1. `AGENTS.md`
2. The files under `guidelines/` (the working method)
3. `instructions.md` (durable product rules)
4. `PLAN.md` (milestone status) and `handoff.md`
5. The owner-selected milestone file under `guidelines/milestones/`
6. `docs/modules/README.md`, the selected owner README/handoff, and only the
   public contracts of relevant dependencies
7. The relevant implementation and tests, as the milestone's existing-state
   check

Run `git status --short` before editing. Preserve owner work and private data.
Do not commit, push, merge, rebase, delete branches, or discard changes unless
explicitly requested.

## Working method change (2026-09-30)

The project now follows the `guidelines/` working method only. The earlier
workflow is retired. This was a documentation change; no application code,
tests, schema, or Makefile target changed.

- `PLAN.md` at the repository root replaces the milestone status index that
  used to be in `instructions.md`. `instructions.md` now holds product rules
  only.
- The eight open milestones (M21E-M21I, M22-M24) moved from the former root
  `milestones/` folder to `guidelines/milestones/` and were restructured into
  the `guidelines/plan.md` format. Their requirements are unchanged. The former acceptance criteria are
  now checkbox completion criteria mirrored in `PLAN.md`; the former ordered
  checklists are the unchecked "Work order" lists.
- The 26 completed milestone files (M1-M21D) moved to `legacy/milestones/`.
  `legacy/` is archived history, never guidance: each file carries a
  `LEGACY — ARCHIVED MILESTONE` banner, and `AGENTS.md` opens with a document
  map marking every path as active or legacy. There is no root `milestones/`
  folder any more.
- Testing scope follows `guidelines/scope.md`: focused checks by default,
  broader checks where a change crosses a shared contract.

## Current state

- M1-M21, the post-M7 linked proposal batches, and the recorded post-M13
  Assistant refinements are complete.
- M21A is complete at revision `d826ac1` (`m21a is done`).
- M21B is complete. Its typed contract, explicit frontend/backend assembly,
  bounded lifecycle handling, shared Platform entry points, compatible
  navigation state, enforcement tests, tightened boundaries, and documented
  extension procedure are implemented in the current uncommitted worktree.
- M21C is complete. Documents owns its errors, scoped CSS, recovery declaration,
  focused fixtures/provider/browser scenarios, and its dependency-closed module
  host.
- M21D is complete. Calendar owns its errors, scoped CSS, typed query/restricted
  command ports, scoped backend/browser tests, and a dependency-closed focused
  host. Courses and Assistant consume Calendar only through public contracts.
- M21E is complete. Courses owns its errors, scoped CSS, bounded public context
  contract, recovery declaration, scoped backend/browser tests, and a
  dependency-closed focused host. Assistant consumes Courses only through its
  public contract.
- M21F is complete. Assistant owns its errors, styles, focused tests, and UI
  orchestration components; shared AI authentication/runtime/workspaces and
  sanitized diagnostics are Platform contracts available independently.
- The owner selected M21E through M21I on 2026-09-30, to be completed in order.
  M21G is the active milestone.
- No feature behavior, schema, storage identity, private data, or visible design
  was changed by M21C/M21D/M21E. M22 was not started.
- The M21A pre-refactor baseline revision is `dcada0a` (`refactoring immense`).
- The observed migration head is `20260908_0021 (head)`.
- The installation identity remains `teacher_assistant`, with its established
  PostgreSQL, Codex-auth, integration-credential, course-content, mail, and
  document storage identities.
- `.openai/hosting.json` is absent; this remains a self-hosted Docker app.

The authoritative milestone state is in `PLAN.md`. Module ownership,
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
- Backend and frontend contract tests now cover duplicate dependency,
  capability, page, and lifecycle declarations. Assembly tests cover missing,
  unknown, and duplicate code contributions; lifecycle tests cover normal and
  exceptional reverse cleanup, aggregate shutdown failures, invalid cleanup
  callbacks, bounded cleanup, and task cancellation.
- Platform's backend boundary allowance now names only the exact configuration,
  error, database, AI, diagnostic, and registration modules it consumes instead
  of granting broad `app.core` or `app.database` access. New negative fixtures
  prove business features cannot import backend assembly internals or bypass the
  frontend Platform facade to reach shell internals.
- Final M21B verification passed `make test` (208 backend and 97 frontend
  tests, boundary/catalog-drift/data-safety gates), the frontend production
  build, `make lint`, and all 12 E2E/accessibility tests.
- Platform and root wiring documentation now records the mirrored metadata,
  owner public entries, static frontend/backend catalogs, root consumers,
  selective-test assembly, lifecycle rules, boundary updates, and module-safe
  shared façades. It explicitly distinguishes metadata-only Settings panels and
  future runtime switches from implemented composition.
- Final verification also confirmed the sole `20260908_0021 (head)` migration,
  healthy isolated database/backend/frontend startup, JSON validity, diff
  hygiene, and removal of isolated test volumes.

## M21C final result

- The existing `app.documents.entry` and `features/documents/entry` surfaces
  remain the only production imports used by Platform composition. The backend
  entry still contributes the existing router and private-root initialization;
  the frontend entry now also owns loading Documents styles.
- Document project/tag not-found and conflict errors plus storage/mismatch
  errors moved from `app.core.errors` to `app.documents.errors`. Their codes,
  statuses, safe messages, and common `ApplicationError` handling are unchanged.
- All existing `.documents-*` and `.document-*` declarations moved from the
  global feature stylesheet to `features/documents/styles.css`, retaining
  desktop and responsive behavior. The delete dialog has equivalent
  Documents-owned selectors instead of borrowing Courses selectors.
- Verification passed 8 focused backend and 2 focused frontend Documents tests,
  `make test` (208 backend and 97 frontend tests plus boundary, catalog-drift,
  and data-safety gates), `make lint`, the frontend production build, and all 12
  isolated E2E/accessibility scenarios. Test stacks and volumes were removed.
- Documents now re-exports a typed recovery declaration containing its unchanged
  manifest key, archive filename/root, format-3 introduction, and archive limits.
  It contains no live path, database/session, repository, restore order, or
  executable callback.
- Platform's coordinated archive helper consumes that declaration for creation,
  manifest build/verification, archive safety checks, and restore. PostgreSQL and
  filesystem quiescence, checksums, restore ordering, format-2 empty-root
  behavior, rollback directories, CLI commands, and scripts remain unchanged.
- Recovery verification passed 18 focused archive tests, including contribution
  validation and simulated document publish-failure rollback. `make
  data-relocation-test` passed the exact coordinated database/private-file drill;
  `make test` passed 217 backend and 97 frontend tests plus all gates, and `make
  lint` passed.
- Platform now owns one shared FastAPI application factory and one shared React
  shell path for full and focused assembly. The allowlisted Documents host closes
  the catalog dependency graph to Platform plus Documents, includes only their
  real routes/pages/lifecycle hooks, and rejects empty, multiple, unknown, or
  path-like module IDs.
- `make dev-module MODULE=documents`, `logs-module`, `down-module`, and
  `test-module` run through the root Docker configuration with a dedicated
  Compose project. Development defaults to UI `15173` and API `18000`; its
  PostgreSQL and every private mount are project-scoped named volumes, so the
  host ran concurrently with the owner application without sharing ports/data.
- Item-3 verification passed 26 backend and 26 frontend focused host/contract
  tests, `make test` (228 backend and 107 frontend tests plus boundary,
  catalog-drift, and data-safety gates), `make lint`, full and module-mode
  production frontend builds, live module API/UI startup, selected/absent route
  checks, invalid-ID command checks, and diff hygiene. The focused stack was
  stopped and temporary test/build volumes were removed.
- Documents API/storage tests now live under `backend/tests/documents/`. Their
  closer fixture mounts the real Platform+Documents host, truncates only
  Documents tables, and uses a private per-test source root. The full-suite
  client imports full application assembly lazily, so focused collection does
  not import it through the root client fixture.
- The stateful frontend fake provider validates Documents methods, paths, and
  payloads and rejects undeclared requests. The owned browser file separately
  exercises real isolated storage and a reversible route-local fake. Neither
  fake is wired into production.
- Focused unit Compose attaches only its isolated database; focused browser
  Compose attaches the database and Documents storage only. A warm complete
  focused run took 37.24 seconds: 34 backend tests in 8.40 seconds, 29 frontend
  tests in 2.04 seconds, and 2 browser tests in 3.7 seconds. This is broader than
  the M21A representative file measurements, so no direct speedup is claimed.
- The boundary manifest has no Documents exception. Production scans passed and
  the deliberate backend/frontend fixtures that import Documents across an
  undeclared boundary were rejected.
- Final M21C verification passed `make test` (228 backend and 108 frontend tests
  plus boundary, contract, and data-safety gates), `make lint`, full and
  module-mode frontend builds, all 13 full browser/accessibility scenarios, and
  exact relocation/backup/restore. The relocation copier ignores deleted
  tracked paths so moved tests are included from an uncommitted worktree.

## M21D final result

- Calendar publishes immutable `CalendarSummary`/`EventSummary` values, bounded
  ID/range/search/availability queries, and a restricted Assistant command port
  from `app.calendar.public`. The command surface omits calendar deletion,
  protection changes, subscriptions, bulk deletion, raw repositories, SQL, and
  a session escape hatch.
- Calendar mutations still pass through `CalendarService`, including read-only,
  source, recurrence, lock, and database guards. Assistant confirmation binds
  the port to its coordinator transaction, flushes with `commit=False`, and
  commits Calendar plus proposal/action/job state once; rollback and repeated
  confirmation tests pass.
- Courses now owns only course-calendar links and uses Calendar's public query
  port for existence/events. Assistant validation, context reads, and execution
  use Calendar's public ports. Calendar application errors moved from Platform
  into `app.calendar.errors` without changing safe codes/statuses/messages.
- The boundary checker permits only the exact declared backend/frontend public
  contracts to graph-approved consumers. All 16 backend and 4 frontend M21D
  legacy exceptions were removed; 22 backend and 3 frontend exceptions remain
  for M21E-M21G.
- Calendar feature selectors moved from the legacy global stylesheet into
  `features/calendar/styles.css`; the Calendar entry loads them. Courses retains
  only its owned embedded-Calendar integration overrides until M21E. The
  existing shell and Calendar visual behavior are unchanged.
- Calendar backend tests now live under `backend/tests/calendar/` with a scoped
  real-host fixture that truncates only events/calendars. The owned browser spec
  independently seeds each workflow and covers create/edit/filter/view/undo,
  accessibility, and read-only event controls.
- The shared focused host now accepts `calendar` and `documents`. Calendar
  assembles only Platform plus Calendar routes/page and the ICS refresh
  lifecycle. Its focused unit/browser stacks attach isolated PostgreSQL and no
  private filesystem storage; subscription networking remains mocked.
- A complete focused Calendar run passed 104 backend tests in 22.75 seconds, 53
  frontend tests in 3.84 seconds, and 2 browser tests in 4.0 seconds. Outer wall
  time was 53.43 seconds including Compose startup, image checks, and cleanup.
- Final full verification passed `make test` (231 backend and 110 frontend tests
  plus boundary, catalog-drift, and data-safety gates), `make lint`, and all 13
  isolated browser/accessibility scenarios in 29.6 seconds. Migration-from-zero
  reached the unchanged `20260908_0021 (head)`.

## M21E final result

- `app.courses.public` publishes a read-only port: bounded course discovery,
  note discovery by whole-word match, bounded note and slide excerpts for
  explicit note IDs, and linked calendar IDs. It returns typed values with
  course/note/source provenance and no ORM entity, repository, session, or
  storage path. Every call is clamped to hard limits and rejects a request
  beyond them.
- Assistant's `course_context.py` keeps the relevance and selection policy and
  now reads only through that port. The four M21E backend boundary exceptions
  were removed; 18 backend and 3 frontend exceptions remain for M21F-M21G. The
  existing course-aware Assistant tests pass unchanged against the real
  contract.
- The 19 Courses error classes moved from `app.core.errors` to
  `app.courses.errors` with unchanged codes, statuses, and messages.
- Course-calendar association keeps link ownership in Courses, reads Calendar
  only through Calendar's read-only query port, and commits once; its
  transaction boundary is documented on `CourseCalendarService`.
- All Courses selectors moved verbatim from the global stylesheet to
  `features/courses/styles.css`, loaded by the Courses entry. Feature sheets
  load before the Platform and global sheets, so five Courses rules that refine
  a shared primitive on the same element now name both classes to keep their
  original effect. A selector-level analysis found no other equal-specificity
  conflict.
- Calendar publishes `calendarEmbeddingClasses`; a contract test holds Courses
  to that list and holds Calendar to providing it.
- Courses supplies a typed recovery contribution with its established archive
  identities. Backup, restore, ordering, and rollback behavior are unchanged.
- Courses backend tests live under `backend/tests/courses/` with a scoped
  fixture on the real focused host and a private per-test course root. The
  400-line combined Course browser scenario was split into seven independently
  seeded scenarios in `e2e/tests/courses.spec.ts` with every original assertion
  retained.
- `courses` is a supported focused host. It assembles Platform, Calendar, and
  Courses only.
- Verification on 2026-09-30: `make test` passed 248 backend and 114 frontend
  tests plus the boundary, contract, and data-safety gates; `make lint` passed;
  `make e2e` passed all 18 browser/accessibility scenarios; full and
  module-mode production builds passed; `make data-relocation-test` passed the
  exact backup/restore drill; the migration head is unchanged; the focused
  Courses run passed 154 backend, 59 frontend, and 7 browser tests in 81
  seconds.

## M21F final result

- Assistant now owns its errors, styles, conversation/proposal UI components,
  scoped backend fixture, and focused browser scenario. Its focused host uses
  real Calendar and Courses providers while Codex remains mocked in ordinary
  tests.
- Platform now exposes reusable AI authentication/runtime/workspace and
  sanitized diagnostic contracts. Settings can manage AI authentication
  without Assistant, while the existing `/assistant/auth*` endpoints remain
  compatible delegates.
- Courses note summary/prettify and both Courses and Assistant diagnostics use
  Platform contracts; no feature imports Assistant internals for shared AI or
  error actions. All 18 M21F backend and the one M21F frontend legacy boundary
  exceptions were removed.
- Assistant proposal execution still shares one transaction with Calendar.
  Diagnostic recording uses an independent transaction, so it cannot commit or
  roll back Assistant state. Cancellation and timeout cleanup immediately
  remove private runtime workspaces.
- Verification on 2026-09-30: `make test-module MODULE=assistant` passed 106
  backend tests, 44 frontend tests, and 1 browser scenario; `make test` passed
  251 backend and 117 frontend tests plus boundary, contract, and data-safety
  gates; `make lint` passed; full and module-mode frontend builds passed; and
  `make e2e` passed all 19 browser/accessibility scenarios. The focused Docker
  host started successfully, both ports responded, and a fresh database reached
  `20260908_0021 (head)`. `git diff --check` passed.

## Shared cautions

- M21C through M21F are complete; M21G-M21I are selected and remain to be done
  in order. Documents, Calendar, Courses, and Assistant own their feature CSS
  and are supported focused hosts. Inbox CSS and its module-host ID remain M21G
  work; Settings module controls remain M21H work.
- Feature stylesheets load before the shared sheets. The earlier Calendar and
  Documents extractions left five elements where a shared rule now wins an
  equal-specificity tie it used to lose (for example `.create-event-button`
  against `.primary-button`). This is a small visual regression from M21C/M21D,
  not yet fixed; M21I owns restoring the original appearance.
- `event-dialog` and `event-form` are dialog primitives defined in Calendar's
  stylesheet and used by Courses and Documents dialogs. Moving them to the
  shared Platform styles is M21I work.
- Backend test files need unique basenames across `backend/tests/` subtrees;
  pytest rejects duplicates when the full suite collects them.
- M22-M24 remain unimplemented: Documents has no editor, compilation, preview,
  or Codex compilation advice.
- The exact boundary manifest is a burn-down list. Remove entries as owning
  milestones migrate them; never broaden an exception to accommodate new code.
- Assistant confirmation binds Calendar's restricted port to one shared
  SQLAlchemy transaction for proposal/job/action and Calendar changes. Preserve
  this atomicity; never expose the session.
- `backend/tests/conftest.py` still resets all tables/private roots for the
  assembled suite. Documents, Calendar, Courses, and Assistant override it with
  scoped fixtures in their owned subtrees. Other owner-specific fixtures,
  remaining feature CSS, and recovery contributions are later-milestone debt.
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
- `guidelines/deployment.md` requires `make up` and `make help`. The Makefile
  provides neither; `make dev` is the current start command and the README
  documents it. This gap is unscheduled and needs an owner decision.

## Exact next step

M21G is active (`guidelines/milestones/m21g-inbox-and-settings-boundary.md`).
M21F is complete and all seven criteria are verified. The owner selected
M21E-M21I; M21H and M21I follow M21G. Do not start M22.

Recommended next prompt:

```text
Continue with M21G.
```
