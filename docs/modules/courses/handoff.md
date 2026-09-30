# Courses handoff

Current state: all completed M8-M18 and course-calendar behavior remains in
place. M21A documented ownership; M21B routed composition through public
entries; M21D moved course-calendar access onto Calendar's public contracts.

M21E made Courses a closed module:

- `app.courses.public` publishes the bounded read-only context and association
  contract. Assistant no longer imports Courses models or repositories.
- Courses errors moved to `app.courses.errors` with unchanged codes, statuses,
  and messages.
- Course styles moved to `features/courses/styles.css`. Five rules that refine a
  shared primitive on the same element now name both classes, because feature
  sheets load before the shared ones.
- Courses' use of Calendar class names is a published, tested contract.
- A typed recovery contribution declares the unchanged course archive
  identities.
- Backend tests live in `backend/tests/courses/` with a scoped fixture on the
  real focused host. The combined browser scenario was split into seven
  independently seeded scenarios in `e2e/tests/courses.spec.ts`.
- `courses` is a supported focused host for `dev-module` and `test-module`.

No feature behavior, schema, storage identity, private data, or visible design
changed.

Verification (2026-09-30): a warm `make test-module MODULE=courses` passed 154
backend tests in 38.73 seconds, 59 frontend tests, and 7 browser scenarios in
12.9 seconds; outer wall time was 81 seconds including Compose startup, image
checks, and cleanup. This selection is broader than the M21A representative
file measurements, so no direct speedup is claimed.
Full-suite results are in the root handoff. Feature evidence remains in
[M18](../../../legacy/milestones/m18-codex-note-prettify.md) and its dependency
milestones rather than being copied here.

Next Courses work: M21F restructures the shared AI runtime behind the Platform
interfaces, which removes Courses' remaining direct `app.ai` and
`app.codex_runtime` imports and the borrowed Assistant error action.
