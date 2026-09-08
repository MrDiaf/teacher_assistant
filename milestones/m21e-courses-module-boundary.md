# M21E - Courses ownership and Calendar integration

- [ ] This milestone

## Outcome

Consolidate the completed Courses workflows behind one feature boundary and
make course-calendar linking and Assistant context use explicit contracts.

Dependency: [M21D](m21d-calendar-module-boundary.md). Planning only. Materials,
notes, summaries, and prettify remain parts of Courses, not new sidebar modules.

## Scope

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

## Ordered checklist

- [ ] Establish the Courses public context and association contracts.
- [ ] Migrate external Course/Note/Source access and Calendar integration.
- [ ] Separate Course UI orchestration/styles and register its module host.
- [ ] Split the long combined Course browser scenario into independently seeded
  CRUD/material/PDF/note/summary/prettify/linking scenarios without losing checks.
- [ ] Scope fixtures and remove Courses boundary exceptions; retain real
  provider/consumer tests for Calendar and Assistant context.
- [ ] Update Courses README/handoff, measurements, and the ownership/status index.

## Acceptance criteria

- No other feature queries Courses-owned repositories/tables or imports its
  internal components; allowed public content queries remain bounded.
- Every previously completed Course workflow passes locally and in the full
  application, including cancellation, failed saves, and deleted/stale IDs.
- Literature and Slides remain distinct; note links and validated citations
  preserve course ownership and provenance.
- Removing a course or association cannot delete Calendar-owned events.
- Shared AI access preserves isolation, explicit suggestion acceptance, and
  existing data limits without real credentials in ordinary tests.
- Course files remain recoverable with matching metadata and hashes through
  coordinated backup/restore; include recovery tests if those adapters move.
- Focused/contract/integration tests, accessibility, lint/build, Docker startup,
  migration compatibility, and diff checks pass.

## Expected implementation areas

Courses, course_sources, notes, course_calendars and their frontend counterparts;
necessary Assistant consumer calls; module styles/fixtures/browser scenarios;
architecture rules; recovery contributions; and Courses documentation.

Stop after verification. [M21F](m21f-assistant-and-ai-platform.md) requires
explicit selection.
