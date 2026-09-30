# M21D - Calendar ownership and public service contract

- [x] This milestone

## Outcome

Make Calendar the sole owner of its business data and mutation rules, with a
public contract supporting its existing UI, Courses, and Assistant consumers.

Dependency: [M21C](m21c-documents-module-pilot.md). Preserve all
completed Calendar behavior; no new scheduling or subscription features.

## Scope

Own calendar/event models, repositories, recurrence, import/subscription logic,
routes, schedulers, frontend interactions, CSS, and tests within Calendar.
Expose typed queries for supplied calendar/event IDs, ranges, search, and
availability plus narrowly defined existing mutation operations. Keep manual
owner operations distinct from the restricted Assistant capability surface.

Read-only enforcement remains in frontend controls, service validation, and
database-changing paths. Public interfaces do not bypass these guards or grant
Assistant calendar deletion, protection changes, bulk deletion, or raw SQL.
Keep UTC/display-timezone handling, recurring scope, idempotency, locks, and
undo behavior consistent with existing tests and completed specifications.

Convert existing external Calendar repository/model access to the public
contract, making only necessary consumer changes in Courses and Assistant.
Deeper restructuring of those consumers belongs to M21E/M21F. Document explicit
transaction coordination so replacing direct repository calls does not turn an
atomic proposal into partially committed actions. Do not add a generic
transaction/session escape hatch to Calendar's public API.

Keep foreign-key integrity and existing migration history. Relocate generic
helpers currently imported from Calendar models to their platform owner.
Extract Calendar-specific CSS, use the shared module host, and split its browser
scenarios into independently seeded tests without relying on another test's
created calendar or persistent UI state.

## Ordered checklist

- [x] Implement Calendar query/mutation contracts and provider contract tests.
- [x] Migrate external Calendar access and generic helper imports; remove the
  corresponding dependency exceptions without broadening permissions.
- [x] Separate Calendar feature styles and UI orchestration where necessary.
- [x] Register subscription lifecycle and focused Calendar test/dev selection.
- [x] Preserve recurrence, permissions, proposal transactions, and imports with
  module tests plus real Courses/Assistant contract integration tests.
- [x] Update Calendar README/handoff, ownership index, timings, and root status.

## Acceptance criteria

- No other feature directly accesses Calendar repositories, ORM entities, or
  tables for business operations; approved integrity/coordinator rules are explicit.
- Calendar works in the shared module host and in the full application with
  unchanged day/week/month, filtering, drag/resize, undo, and ICS workflows.
- Protected-event and recurring-event behavior passes at all existing layers;
  invalid IDs and mutation attempts fail with compatible safe errors.
- Course-linked calendars and confirmed Assistant proposals still work through
  the real public contract, including rollback and repeated confirmation.
- Isolated tests never contact real subscriptions or use owner storage.
- Focused/contract/integration tests, shell smoke, accessibility, lint/build,
  Docker startup, migration compatibility, and diff checks pass.

## Expected implementation areas

Calendar backend/frontend/styles/tests, its public contract, necessary consumer
call sites, platform utilities, lifecycle registration, architecture checks,
module host configuration, and Calendar documentation. No Calendar redesign.

Stop after verification. [M21E](m21e-courses-module-boundary.md) requires explicit
selection.
