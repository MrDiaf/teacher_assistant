# M17 — Summary decluttering and removable summary bullets

- [ ] This milestone

## Outcome

Reduce visual clutter by allowing each AI summary to be minimized and expanded,
and let the owner remove individual generated summary bullets they do not want.

“Remove” in this milestone applies only to a generated summary bullet. It must
never delete or edit the source note, linked slide references, uploaded files,
or extracted slide text.

## Minimize and expand behavior

- Add a clear minimize/expand control to every summary section.
- Keep a compact header visible while minimized, including summary state,
  model, stale warning when applicable, and bullet count.
- Use `aria-expanded` and a readable accessible label.
- Do not discard an in-progress summary job or error state merely because the
  section is minimized.
- M17 may retain collapse state while the page remains mounted. M19 will make
  the preference survive navigation/reload.

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

- [ ] Add backend-owned stable IDs to persisted summary bullets.
- [ ] Migrate or compatibly backfill existing summaries.
- [ ] Add a validated remove-one-bullet service and API route.
- [ ] Make repeated/concurrent removal idempotent or safely conflicting.
- [ ] Add minimize/expand controls and compact summary headers.
- [ ] Add an accessible cross button to each completed bullet.
- [ ] Add empty-summary, busy, and persistence-failure states.
- [ ] Preserve stale-summary and provenance behavior.
- [ ] Add backend schema, migration, service, and API tests.
- [ ] Add frontend interaction and accessibility tests.
- [ ] Add E2E coverage for minimize, expand, remove, reload, and regenerate.
- [ ] Update documentation.

## Acceptance criteria

- The owner can minimize and expand each note summary independently.
- A minimized summary clearly shows what it is and whether it is stale.
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
