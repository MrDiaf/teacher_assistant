# Teacher Assistant development handoff

Updated: 2026-08-31

## Start here

Read these files completely before planning or changing code:

1. `AGENTS.md`
2. `instructions.md`
3. `handoff.md`
4. The owner-selected file under `milestones/`
5. The relevant implementation and tests

The milestone status index in `instructions.md` is authoritative. The selected
milestone file is the implementation boundary for a development session.
The active documentation set is self-contained and does not require any
retired specification file. Historical instruction files may be removed later
without affecting the reading order or milestone handoffs.

Run `git status --short` before editing and preserve all owner work. Do not
commit, push, merge, rebase, delete branches, or discard changes unless the
owner explicitly asks.

## Current state

- Git `HEAD`: `8f0eb0e milestones done`
- M1 through M14 are complete.
- The post-M7 linked Assistant proposal-batch milestone is complete.
- The post-M13 Assistant diagnostics, general-helper routing, bounded automatic
  correction, working-state display, cancellation, and false course-note
  matching refinements are complete and committed in `a14781d`.
- M15 through M19 are planned, but no implementation milestone is active.
- The current uncommitted worktree is the completed M14 implementation and its
  documentation. Preserve it; no commit was requested.
- The installation now has stable identity `teacher_assistant`, resolving to
  `teacher_assistant_database-data` and
  `teacher_assistant_codex-auth-data`. The private `.env` and ignored
  `.teacher-assistant-installation` marker were created during non-destructive
  same-namespace adoption.
- Docker development services are running:
  - frontend: `http://localhost:5173`
  - backend: `http://localhost:8000`
  - PostgreSQL: healthy
- Alembic is at `20260731_0017 (head)`.
- `.openai/hosting.json` is absent. This is a self-hosted Docker application,
  not a Sites deployment.

Recheck instead of trusting this snapshot at the start of the next session:

```bash
git status --short
docker compose -f compose.yml -f compose.dev.yml ps
docker compose -f compose.yml -f compose.dev.yml exec -T backend alembic current
```

## Implemented product surface

- Calendar: local/imported/subscribed calendars; day, week, and month views;
  recurrence; drag/move/resize; search/filter; read-only protection; ICS import
  and subscriptions.
- Assistant: private conversations, bounded calendar/course context, model
  selection, validated calendar proposals, separate confirmations, linked
  creation batches, retries, diagnostics, progress, and cancellation.
- Courses: manual CRUD/archive/restore, private Literature and Slides storage,
  extraction, notes and slide references, AI summaries with provenance,
  course-linked calendars, and course-aware Assistant answers.
- Dashboard, Study Plan, and Settings remain placeholder modules unless the
  owner defines a new milestone.

The permanent safety and architecture rules are in `AGENTS.md` and
`instructions.md`. Do not duplicate or weaken them in a new milestone.

## Most recent completed work

M14 data durability, relocation, and update safety:

- pins a stable, configurable per-installation Compose identity and records an
  ignored initialization marker so a missing initialized database fails closed;
- provides read-only `make data-preflight`, explicit new-clone initialization,
  and preflighted `make data-adopt` with stopped-source checks, copy digests,
  populated-target refusal, rollback records, and no automatic old-volume
  deletion;
- keeps host course storage configurable through `COURSE_DATA_DIR` and mounts
  Codex auth at the configured persistent path;
- creates unique coordinated PostgreSQL/course-file backup bundles with private
  permissions, JSON manifests, byte counts, SHA-256 checksums, dump listing,
  and safe archive validation;
- restores only after validation and exact identity confirmation, takes a fresh
  safety backup first, retains the prior course directory, runs migrations, and
  excludes renewable Codex credentials;
- documents persistent/disposable data, two-clone isolation, supported stopped
  moves/renames, updates, rollback, backup, and clean restore;
- adds a non-private end-to-end fixture drill for legacy adoption, migration,
  rebuild, same-name move, rename, multi-clone isolation, backup/restore, and
  corrupt/mismatched-data refusal.

Important implementation areas:

```text
compose.yml
.env.example
Makefile
scripts/data-safety.sh
scripts/data-backup.sh
scripts/data-restore.sh
scripts/m14-relocation-drill.sh
backend/app/maintenance/data_archive.py
backend/tests/test_data_archive.py
docs/data-durability.md
```

## Last full verification recorded

The latest implementation handoff recorded:

```text
make test
  Backend: 114 passed
  Frontend: 39 passed

make e2e
  Playwright/accessibility: 8 passed

make lint: passed
make data-relocation-test: passed
make data-preflight: passed
make backup: passed (dump listing, archive read, manifest/checksums)
Frontend production build: passed
git diff --check: passed
Alembic current: 20260731_0017 (head)
Backend health: passed
Frontend HTTP check: passed
Existing ChatGPT auth after adoption/rebuild: connected
```

Ordinary tests mock Codex. Real Codex features require private ChatGPT sign-in
from Assistant or the optional configured API-key fallback.

## Planned milestone sequence

- [x] M14 — PostgreSQL, uploads, configuration, and Docker volumes are safe
  across supported `mv`, rebuild, migration, backup, and restore workflows.
- [ ] M15 — Stream uploaded PDFs safely by source ID, show them inside Teacher
  Assistant, and allow a separate browser window/tab.
- [ ] M16 — Add a lightweight Markdown-aware note editor where syntax markers
  remain visible while their content is styled, plus safe Markdown rendering.
- [ ] M17 — Minimize/expand summaries and persistently remove individual
  generated bullets without touching source notes or slides.
- [ ] M18 — Add a Codex Prettify suggestion workflow with isolated context,
  strict validation, before/after preview, explicit acceptance, and no automatic
  note save.
- [ ] M19 — Persist selected pages/views and per-conversation Assistant drafts
  in validated browser storage without caching authoritative backend data.

The full scope, boundaries, checklist, acceptance criteria, and expected files
are in the corresponding milestone files. Do not combine or automatically
advance them.

## Known limitations and cautions

- M15–M19 are plans only and none of their application behavior exists yet.
- Read-only preflight found another populated legacy database-volume candidate
  on this Docker host. It was intentionally left untouched. Never merge or
  delete it implicitly; any later cleanup requires explicit owner verification.
- Clean restore does not copy Codex credentials. Authentication is renewable;
  sign in again when the target installation has no session.
- Historical Assistant failures cannot recover validation detail that was never
  stored; retrying creates current structured diagnostics if failure repeats.
- Automatic correction is limited to one response-schema/citation retry.
- Cancellation coordination is in-process and assumes the current
  single-process backend; multiple workers would need shared coordination.
- General help has no live web access, code execution, clipboard control, or
  interactive editor.
- Private course content is attached only for explicit note/slide intent; an
  ambiguous topic-only question uses general model knowledge.
- `Ask Assistant about this error` is not exposed for every application error.
- Diagnostic records have no owner-facing purge UI.
- `alembic check` may report four pre-existing enum/VARCHAR length differences:
  `assistant_messages.role`, `assistant_proposals.status`,
  `calendars.source_type`, and `events.status`.
- Automatic LMS/course import, assignments, Study Plan, and new modules require
  an owner-defined milestone.

## Next step

M14 is complete. Stop before M15. The owner must explicitly select M15 before
PDF-viewing implementation begins.

Recommended next prompt:

```text
Read AGENTS.md, instructions.md, handoff.md, and
milestones/m15-pdf-viewing.md. Implement M15 only and stop after its acceptance
criteria are verified.
```
