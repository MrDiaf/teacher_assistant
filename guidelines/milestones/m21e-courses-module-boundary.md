# M21E - Courses ownership and Calendar integration

## Objective

Consolidate the completed Courses workflows behind one feature boundary and
make course-calendar linking and Assistant context use explicit contracts.

## Dependencies

Requires M21D to be complete because this milestone consumes Calendar's public
query and command contracts. M21D is complete; inspect the resulting repository
state first and read its
[archived milestone file](../../legacy/milestones/m21d-calendar-module-boundary.md)
only if historical intent is required.

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

Authorized areas: Courses, course_sources, notes, course_calendars and their
frontend counterparts; necessary Assistant consumer calls; module
styles/fixtures/browser scenarios; architecture rules; recovery contributions;
and Courses documentation.

Not authorized:

- Materials, notes, summaries, and prettify remain parts of Courses, not new
  sidebar modules.
- Assistant's routing/context-selection policy and AI provider restructuring
  belong to M21F.
- Do not redesign the editor.

Stop after verification. M21F requires explicit owner selection.

## Required work

Courses owns course records, materials/extraction/storage, notes/slide links,
summary provenance and bullets, prettify workflow, and course-calendar
association records. Preserve the established internal service/repository
separation. Group ownership without forcing all implementation into one file.

Expose bounded course discovery and note/slide context interfaces required by
Assistant. Return explicit data contracts with provenance, not ORM entities or
unrestricted content access. Move Assistant's direct Course/Note/Source queries
to those interfaces; keep its routing/context-selection policy for M21F.

Use Calendar's public contract for linked-calendar queries and changes. Keep
link ownership in Courses, make required transaction boundaries explicit, and
preserve calendar/event records when a course is deleted. Retain current
foreign-key rules and same-course slide-reference checks.

Courses uses the platform AI/model/runtime contract established in M21B. The
summary/prettify validators and owner acceptance/save rules remain Courses
responsibilities. Shared model authentication must not require mounting the
Assistant page; provider restructuring is completed in M21F.

Split large page orchestration and CSS along existing Courses responsibilities
where it improves isolation. Preserve Markdown source, undo/caret behavior,
PDF viewing, note disclosure resets, bullet IDs/removal, summary staleness,
unsaved drafts, and course-scoped navigation state. Do not redesign the editor.

### Work order

1. Establish the Courses public context and association contracts.
2. Migrate external Course/Note/Source access and Calendar integration.
3. Separate Course UI orchestration/styles and register its module host.
4. Split the long combined Course browser scenario into independently seeded
   CRUD/material/PDF/note/summary/prettify/linking scenarios without losing
   checks.
5. Scope fixtures and remove Courses boundary exceptions; retain real
   provider/consumer tests for Calendar and Assistant context.
6. Update Courses README/handoff, measurements, the ownership index, and
   `PLAN.md`.

## Completion criteria

- [ ] No other feature queries Courses-owned repositories/tables or imports its
  internal components; allowed public content queries remain bounded.
- [ ] Every previously completed Course workflow passes locally and in the full
  application, including cancellation, failed saves, and deleted/stale IDs.
- [ ] Literature and Slides remain distinct; note links and validated citations
  preserve course ownership and provenance.
- [ ] Removing a course or association cannot delete Calendar-owned events.
- [ ] Shared AI access preserves isolation, explicit suggestion acceptance, and
  existing data limits without real credentials in ordinary tests.
- [ ] Course files remain recoverable with matching metadata and hashes through
  coordinated backup/restore; include recovery tests if those adapters move.
- [ ] Focused/contract/integration tests, accessibility, lint/build, Docker
  startup, migration compatibility, and diff checks pass.

## Verification

This milestone changes public contracts and shared fixtures, so verification
covers Courses and its affected consumers (Calendar, Assistant) rather than
Courses alone.

- Focused Courses tests plus real provider/consumer contract and integration
  tests for Calendar and Assistant context, with Codex mocked.
- `make check-boundaries` with no remaining Courses exception.
- Browser and accessibility scenarios for the split Course workflows
  (`make e2e`).
- `make test` as the affected-consumer gate for the changed contracts.
- `make lint` and the frontend production build.
- Docker startup and migration compatibility.
- Coordinated backup/restore (`make data-relocation-test`) if recovery adapters
  move.
- `git diff --check`.
