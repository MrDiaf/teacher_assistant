# M17 — Minimized notes, summary decluttering, and removable bullets

- [x] This milestone

Status: **complete and verified 2026-09-01**.

## Outcome

Reduce visual clutter by making every course note and its AI summary start in a
minimized state whenever the owner enters the Notes page. The owner can expand
notes and summaries independently and remove individual generated summary
bullets they do not want.

“Remove” in this milestone applies only to a generated summary bullet. It must
never delete or edit the source note, linked slide references, uploaded files,
or extracted slide text.

## Note minimize and expand behavior

- Every note card starts minimized whenever the Notes view mounts, including
  initial entry, page reload, returning from another module, and returning from
  another course tab.
- A newly created note also enters the list minimized.
- A minimized note keeps a compact header visible with its title, last-updated
  date, slide-reference count, and a concise summary-state indicator when one
  exists.
- Expanding one note reveals only that note's body, Markdown content,
  references, actions, and summary section. It must not expand other notes.
- Edit and destructive actions must remain clearly labeled and must not be
  triggered by the expand/collapse control.
- Use a real button with `aria-expanded`, `aria-controls`, a readable label,
  visible focus, and keyboard operation.
- Expansion lasts only for the current mounted Notes visit. Leaving and
  returning deliberately restores the uncluttered all-minimized layout.

## Summary minimize and expand behavior

- Every summary starts minimized, independently of its containing note. Opening
  a note must not automatically expand its summary.
- Add a clear minimize/expand control to every summary section.
- Keep a compact header visible while minimized, including summary state,
  model, stale warning when applicable, and bullet count.
- Use `aria-expanded`, `aria-controls`, and a readable accessible label.
- Do not discard an in-progress summary job or error state merely because the
  section is minimized.
- A summary that finishes or is regenerated remains minimized until the owner
  explicitly expands it; its compact header announces the updated state.
- Summary expansion lasts only for the current mounted Notes visit. M19 must
  not persist or restore note/summary expanded states.

## Individual bullet removal

Each completed bullet receives a small cross button at its side with an
accessible label such as `Remove summary bullet 2`. Pressing it removes only
that bullet from the persisted current summary.

Current summary bullets have no stable server-owned identifier. Add a stable
identifier assigned by backend code after Codex output validation; Codex must
not choose or be trusted to provide it. Existing saved summaries must remain
readable and receive safe identifiers through a migration or compatible
backfill path.

Use an endpoint based on summary ID and bullet ID rather than accepting an
arbitrary replacement `summary_json` from the browser. Revalidate the summary,
bullet ownership, current state, and remaining provenance before committing.
Concurrent or repeated removal must be safe and must not remove a different
bullet after list indexes shift.

If the final bullet is removed, keep a clear empty-summary state with a
**Generate again** action. Regeneration creates a fresh validated summary and
may produce content similar to a previously removed bullet.

## Safety and error behavior

- Do not mutate summary provenance or citations for remaining bullets.
- Do not allow bullet removal from a running/failed summary as though it were a
  completed result.
- Disable only the affected controls while a request is active.
- If persistence fails, restore/show the bullet and display a readable error.
- Do not send a removal request to Codex; this is an ordinary owner-controlled
  backend mutation.
- Do not expose raw summary JSON or allow removal by array index alone.

## Completed checklist

- [x] Add backend-owned stable IDs to persisted summary bullets.
- [x] Migrate or compatibly backfill existing summaries.
- [x] Add a validated remove-one-bullet service and API route.
- [x] Make repeated/concurrent removal idempotent or safely conflicting.
- [x] Make every note initialize minimized on every Notes-view mount.
- [x] Add independent note minimize/expand controls and compact note headers.
- [x] Make every nested summary initialize minimized independently.
- [x] Add independent summary controls and compact summary headers.
- [x] Keep new and regenerated note/summary content minimized until explicitly
  expanded.
- [x] Add an accessible cross button to each completed bullet.
- [x] Add empty-summary, busy, and persistence-failure states.
- [x] Preserve stale-summary and provenance behavior.
- [x] Add backend schema, migration, service, and API tests.
- [x] Add frontend interaction and accessibility tests.
- [x] Add E2E coverage for default minimization, independent expansion,
  navigation return, reload, remove, and regenerate.
- [x] Update documentation.

## Acceptance criteria

- Every note is minimized when the owner enters or returns to the Notes page.
- Every nested summary is also minimized by default, even after its note is
  expanded.
- Notes and summaries expand independently; opening one does not open any
  sibling note or nested summary.
- Minimized note headers identify the note and show useful counts/state without
  displaying the full body.
- A minimized summary clearly shows what it is and whether it is stale.
- Leaving and returning to Notes resets every note and summary to minimized,
  including after M19 adds persistence for other frontend state.
- Pressing a bullet's cross removes that exact generated bullet after a reload.
- Removing one bullet leaves every other bullet and its provenance unchanged.
- Repeating the same request cannot remove the next bullet accidentally.
- Removing the final bullet produces a useful empty state and does not remove
  the source note.
- Existing summaries created before the milestone remain usable.
- Summary generation, retry, staleness, source hashes, citations, and note CRUD
  continue to work.
- Relevant migrations, tests, lint, build, and Docker checks pass.

## Expected implementation areas

```text
backend/app/notes/summary_models.py
backend/app/notes/summary_schemas.py
backend/app/notes/summary_validation.py
backend/app/notes/summary_repository.py
backend/app/notes/summary_service.py
backend/app/notes/summary_routes.py
backend/alembic/versions/
backend/tests/test_note_summaries.py
frontend/src/features/courses/CourseNotes.tsx
frontend/src/features/courses/api.ts
frontend/src/features/courses/types.ts
frontend/src/styles.css
frontend Courses and E2E tests
README.md
```

Deleting whole notes, deleting source files, and using Codex to decide which
bullets to remove are outside this milestone.
