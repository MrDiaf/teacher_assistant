# M21I - Modular verification, Docker workflow, and refactoring completion

## Objective

Complete and measure the development/test workflow across every existing
module, verify the assembled application and upgrade/recovery paths, and close
the refactoring sequence before any M22-M24 feature implementation.

## Dependencies

Requires M21H to be complete because the configuration matrix below verifies
its module controls. Inspect the resulting repository state first; read
[M21H](m21h-module-controls-and-lifecycle.md) only if additional intent is
required.

Earlier milestones must already have tested their changes; this is not deferred
testing.

This milestone is planned, not active, until the owner selects it.

## Existing-state check

Before making changes:

1. Inspect the relevant repository state.
2. Evaluate every completion criterion below.
3. Mark criteria that are already satisfied, here and in
   [PLAN.md](../../PLAN.md).
4. Run the smallest relevant verification when necessary.
5. If every criterion is already satisfied, mark the milestone complete and
   make no implementation changes.
6. Otherwise, preserve existing correct work and implement only what is missing.

Do not read other milestone files unless they are necessary to resolve
information that cannot be determined from the repository or current
instructions.

## Scope

Authorized areas: Makefile, shared Compose/test overrides, fixtures/test
factories, module host, module/platform test suites, architecture checks,
synthetic upgrade/recovery drills, README and module documentation,
`PLAN.md`/handoff, and future milestone path corrections.

Not authorized: do not add the LaTeX editor, compiler, or advice
implementation.

Stop after verification. The next planned feature is M22; it still requires
explicit owner selection.

## Required work

Finish the reusable module host and focused commands introduced in M21C for
Calendar, Courses, Assistant, Inbox, Documents, and platform checks. Reuse one
maintained Docker setup and image/dependency caches. Module overrides contain
only necessary differences; app selection chooses modules, while Compose
profiles choose services. Ordinary `make dev` continues to start the full app.

Provide separate checks for boundaries, module tests, contracts, real integration
workflows, shell smoke, and full regression/recovery. Preserve `make test`,
`make e2e`, and all other established root commands as complete entry points.
Every focused run must report its selected scope so it cannot be mistaken for
full verification. Unknown selectors fail rather than silently running nothing.

Scope pure tests without global database/storage cleanup. Give integration
tests their required real PostgreSQL/storage fixtures. Central migrations may
still prepare a complete test schema; do not pretend schema preparation costs
have disappeared. Distinguish schema setup from per-test/runtime isolation.
Browser scenarios must seed/clean their own data. Parallelize only where
database/schema, storage, ports, fixtures, and caches are safely isolated.
Test commands must never attach or truncate the owner's databases/volumes.

Document change-based verification: module internals need focused tests;
contract changes also need affected consumers and real integrations; shell,
configuration, migrations, storage/recovery, or dependency changes need broader
checks. Retain required final full regression and durability gates. Mocks must
be checked against providers; passing independent mock suites is insufficient.

### Work order

1. Complete all module/platform commands and shared host configurations.
2. Finish fixture and browser-scenario isolation without dropping assertions.
3. Enforce all ownership/import rules with no legacy migration allowances;
   verify deliberate invalid-import fixtures fail the architecture check.
4. Add a bounded configuration matrix: all enabled, each feature disabled,
   each feature with required platform only, optional capability absence, and
   invalid dependency combinations. Cover real critical module integrations.
5. Compare reproducible cold/warm focused and full timings against M21A;
   report medians from repeated representative runs and investigate regressions.
6. Verify an upgrade from committed M21 using synthetic populated data, plus
   clean restore, rollback, relocation, and clone isolation with exact hashes.
7. Finish ownership/README/handoff documentation and update M22-M24 expected
   implementation paths to the resulting public entries/module-owned styles.
8. Record final evidence and mark the refactoring sequence complete only
   when its criteria pass; leave M22 unselected.

## Completion criteria

- [ ] Every implemented module can mount through the same entry in the real app
  and focused host; a module-local test does not launch unrelated runtime jobs.
- [ ] Feature styles are owned locally; global CSS contains documented shared
  primitives/shell rules, with original desktop/mobile appearance preserved.
- [ ] No business module bypasses another module's public interface. Public
  contracts and explicit transaction coordinators preserve integrity checks.
- [ ] Module-local iteration can occur without editing shell rendering or root
  feature CSS; provider contract changes correctly select consumer verification.
- [ ] Measurements demonstrate reduced unrelated work and a shorter
  representative warm focused loop than full verification on the same
  environment; avoid a promised percentage or fixed duration unsupported by
  measurements.
- [ ] All-enabled and disabled-module configurations preserve data and supported
  workflows; coordinated backups include retained data even when disabled.
- [ ] Full tests, contracts, architecture checks, E2E/accessibility, lint,
  production build, Docker startup, migrations/upgrade, recovery drills, and
  diff checks pass. Known pre-existing schema drift is recorded separately, not
  hidden.
- [ ] Root documentation is a concise current index; a developer follows one
  module's scope/handoff and relevant public contracts for ordinary local work.

## Verification

This is the refactoring sequence's final gate, so full verification is the
required scope here rather than a focused target.

- Every module/platform focused command, each reporting its selected scope.
- `make check-boundaries` with no legacy allowances, and the deliberately
  invalid import fixtures rejected.
- `make check-module-contract`.
- `make test` and `make e2e` (browser and accessibility).
- The bounded configuration matrix described above.
- `make lint` and the frontend production build.
- Docker startup, migration-from-zero, and the upgrade from committed M21 with
  synthetic populated data.
- Recovery drills: clean restore, rollback, relocation, and clone isolation
  with exact hashes (`make data-relocation-test`, `make data-safety-test`).
- Repeated cold/warm timing runs compared against the M21A baseline.
- `git diff --check`.
