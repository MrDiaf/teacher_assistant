# M21I - Modular verification, Docker workflow, and refactoring completion

- [ ] This milestone

## Outcome

Complete and measure the development/test workflow across every existing
module, verify the assembled application and upgrade/recovery paths, and close
the refactoring sequence before any M22-M24 feature implementation.

Dependency: [M21H](m21h-module-controls-and-lifecycle.md). Planning only. Earlier
milestones must already have tested their changes; this is not deferred testing.

## Scope

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

## Ordered checklist

- [ ] Complete all module/platform commands and shared host configurations.
- [ ] Finish fixture and browser-scenario isolation without dropping assertions.
- [ ] Enforce all ownership/import rules with no legacy migration allowances;
  verify deliberate invalid-import fixtures fail the architecture check.
- [ ] Add a bounded configuration matrix: all enabled, each feature disabled,
  each feature with required platform only, optional capability absence, and
  invalid dependency combinations. Cover real critical module integrations.
- [ ] Compare reproducible cold/warm focused and full timings against M21A;
  report medians from repeated representative runs and investigate regressions.
- [ ] Verify an upgrade from committed M21 using synthetic populated data, plus
  clean restore, rollback, relocation, and clone isolation with exact hashes.
- [ ] Finish ownership/README/handoff documentation and update M22-M24 expected
  implementation paths to the resulting public entries/module-owned styles.
- [ ] Record final evidence and mark the refactoring sequence complete only
  when its criteria pass; leave M22 unselected.

## Acceptance criteria

- Every implemented module can mount through the same entry in the real app
  and focused host; a module-local test does not launch unrelated runtime jobs.
- Feature styles are owned locally; global CSS contains documented shared
  primitives/shell rules, with original desktop/mobile appearance preserved.
- No business module bypasses another module's public interface. Public
  contracts and explicit transaction coordinators preserve integrity checks.
- Module-local iteration can occur without editing shell rendering or root
  feature CSS; provider contract changes correctly select consumer verification.
- Measurements demonstrate reduced unrelated work and a shorter representative
  warm focused loop than full verification on the same environment; avoid a
  promised percentage or fixed duration unsupported by measurements.
- All-enabled and disabled-module configurations preserve data and supported
  workflows; coordinated backups include retained data even when disabled.
- Full tests, contracts, architecture checks, E2E/accessibility, lint, production
  build, Docker startup, migrations/upgrade, recovery drills, and diff checks
  pass. Known pre-existing schema drift is recorded separately, not hidden.
- Root documentation is a concise current index; a developer follows one
  module's scope/handoff and relevant public contracts for ordinary local work.

## Expected implementation areas

Makefile, shared Compose/test overrides, fixtures/test factories, module host,
module/platform test suites, architecture checks, synthetic upgrade/recovery
drills, README and module documentation, status/handoff, and future milestone
path corrections. Do not add the LaTeX editor, compiler, or advice implementation.

After verification, the next planned feature is
[M22](m22-relative-latex-editor.md). It still requires explicit owner selection.
