# M21C - Documents module and isolated development pilot

- [ ] This milestone

## Outcome

Use the existing Documents foundation to prove module ownership, scoped styles,
isolated testing, and a reusable development host before migrating other areas.

Dependency: [M21B](m21b-application-composition.md). Planning only. Preserve the
M21 feature boundary; do not implement the M22 editor or any compiler/advice UI.

## Scope

Make Documents own its frontend, API contracts, services, repository, models,
filesystem storage, feature styles, and test fixtures. Expose only its public
module entry and required platform-facing interfaces. Move files only where
this clarifies ownership; a folder rename alone does not satisfy the milestone.

Extract Documents CSS from the global stylesheet without changing appearance.
Keep immutable project IDs, endpoints, tag behavior, download headers, initial
`main.tex`, source paths, archive contents, and explicit deletion confirmation.
Preserve atomic creation and quarantine/rollback/purge semantics.

Provide a Documents-owned recovery contribution through an explicit platform
interface. The platform still coordinates database/filesystem quiescence,
manifest verification, rollback, and supported old backup formats. Do not move
recovery into an independent per-module backup that can disagree with PostgreSQL.

Build one shared development/test host using the real shell and module entry.
Support a Documents UI with contract-checked fake responses for UI work and
Documents with its real backend plus isolated PostgreSQL/filesystem fixtures.
Fakes and fixture routes must not be enabled in ordinary application startup.
Do not copy the shell into a separate mock website or create another frontend.

Add documented root commands such as `make dev-module MODULE=documents` and
`make test-module MODULE=documents`. The final command names may follow local
patterns but must reject unknown IDs and run entirely through Docker. Reuse
the root Compose images/configuration with a bounded development override;
test data and ports must be separate from the owner's running installation.
Selective bootstrap must avoid unrelated schedulers and per-test storage wipes.

## Ordered checklist

- [ ] Establish Documents public entry points, internal ownership, and scoped CSS.
- [ ] Connect Documents recovery through a tested platform contribution.
- [ ] Implement the shared module host and initial focused Docker commands.
- [ ] Separate Documents fixtures and backend/frontend/browser scenarios while
  retaining real API/storage coverage and fake/provider contract checks.
- [ ] Remove Documents boundary exceptions and verify forbidden access fails.
- [ ] Measure focused checks against M21A; document the module workflow, storage
  contract, timings, limitations, and next step in its README/handoff.

## Acceptance criteria

- Documents can be developed and tested using the real shell without running
  Calendar, Courses, Inbox, or Assistant background activity.
- Module tests preserve M21 CRUD, tag, path, source-download, failed transaction,
  and deletion protections using private isolated fixtures.
- Full-app navigation and unrelated page appearance remain intact; desktop,
  mobile, keyboard, and accessibility checks pass.
- Coordinated backup/restore and relocation reproduce exact source hashes and
  metadata, including rollback failures and format-2 compatibility.
- Focused runs demonstrably omit unrelated test work; record measured elapsed
  times without claiming unmeasured speedups or dropping coverage for speed.
- A small reversible fixture-only UI exercise proves module-local iteration
  without changes to shell rendering, global feature CSS, or production data.
- Relevant focused/contract tests, full-app smoke, lint/build, Docker startup,
  recovery checks, and `git diff --check` pass.

## Expected implementation areas

Documents frontend/backend/styles/tests, shared module host, selected app/test
factories, archive coordinator interface, isolated fixtures, Makefile/Compose
development overrides, and Documents/platform documentation. Update the index
and handoff only after verification; do not mark other modules isolated yet.

Stop after verification. [M21D](m21d-calendar-module-boundary.md) requires
explicit selection.
