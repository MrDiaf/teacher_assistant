# Teacher Assistant development handoff

Updated: 2026-09-01

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

- Git `HEAD`: `eab1686 good with markdown`
- M1 through M17 are complete.
- The post-M7 linked Assistant proposal-batch milestone is complete.
- The post-M13 Assistant diagnostics, general-helper routing, bounded automatic
  correction, working-state display, cancellation, and false course-note
  matching refinements are complete and committed in `a14781d`.
- M18 through M22 are planned, but no implementation milestone is active.
- The current uncommitted worktree contains the completed M17 implementation
  and documentation, owner-selected M17/M19 refinements, and the new M20–M22
  Canvas/Inbox/mail plans. Preserve it; no commit was requested.
- The installation now has stable identity `teacher_assistant`, resolving to
  `teacher_assistant_database-data` and
  `teacher_assistant_codex-auth-data`. The private `.env` and ignored
  `.teacher-assistant-installation` marker were created during non-destructive
  same-namespace adoption.
- Docker development services are running:
  - frontend: `http://localhost:5173`
  - backend: `http://localhost:8000`
  - PostgreSQL: healthy
- Alembic is at `20260831_0018 (head)`.
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
  extraction, in-app and new-window PDF viewing, notes and slide references, AI
  summaries with provenance, course-linked calendars, and course-aware
  Assistant answers.
- Dashboard and Study Plan remain placeholder modules. Settings also remains a
  placeholder until the planned M20 integration work is explicitly selected
  and implemented; Inbox does not exist until M21.

The permanent safety and architecture rules are in `AGENTS.md` and
`instructions.md`. Do not duplicate or weaken them in a new milestone.

## Most recent completed work

M17 minimized notes, summary decluttering, and removable bullets:

- starts every note minimized on each Notes-tab mount and keeps a compact title,
  updated date, slide-reference count, and summary indicator visible;
- expands each note independently with accessible disclosure controls, while
  keeping its nested summary independently minimized until explicitly opened;
- resets all disclosure state when leaving and returning, on reload, between
  courses, and for newly created notes;
- assigns backend-owned UUIDs after Codex summary validation without adding IDs
  to the Codex output schema;
- migrates existing saved bullets and retains a compatible runtime backfill;
- removes one completed bullet through a summary-ID/bullet-ID endpoint under a
  row lock, revalidates the stored result and provenance, and safely conflicts
  on repeated or stale IDs;
- preserves every remaining bullet and citation exactly, retains the source
  note and slides after final-bullet removal, and offers Generate again from a
  clear empty state;
- keeps only the affected remove control busy, leaves a bullet visible when
  persistence fails, and includes keyboard, accessibility, navigation, reload,
  removal, regeneration, migration, and safety coverage.

Important M17 implementation areas:

```text
backend/alembic/versions/20260831_0018_summary_bullet_ids.py
backend/app/notes/summary_{validation,repository,service,routes,schemas}.py
backend/tests/test_note_summaries.py
frontend/src/features/courses/{CourseNotes,CoursesPage.test}.tsx
frontend/src/features/courses/{api,types}.ts
frontend/src/styles.css
e2e/tests/calendar-assistant.spec.ts
README.md
```

## Previous completed work

M16 lightweight Markdown note editing:

- replaces the note-body textarea with a dependency-free native textarea and
  synchronized inert highlighting layer, so source markers remain visible and
  native caret, selection, copy/paste, and browser undo behavior remain intact;
- highlights headings, bold, italic, ordered and unordered lists, blockquotes,
  links, inline code, and fenced code blocks while retaining a one-click plain
  text fallback;
- adds toolbar formatting, Ctrl/Cmd+B and Ctrl/Cmd+I selection shortcuts,
  accessible labels, focus behavior, and a visible 100,000-character state;
- renders the supported subset on note cards with semantic React elements,
  never injects HTML, and disables unsafe link schemes and active embeds;
- preserves the exact source Markdown in API storage, slide-reference editing,
  summary input and staleness behavior, and all existing note ownership rules;
- adds unit, integration, backend round-trip/limit, XSS, malformed input,
  keyboard/undo, E2E, responsive, and accessibility coverage;
- documents the supported owner workflow and safety behavior.

Important implementation areas:

```text
backend/tests/test_course_notes.py
frontend/src/features/courses/{MarkdownNoteEditor,SafeMarkdown}.tsx
frontend/src/features/courses/{MarkdownNoteEditor,SafeMarkdown}.test.tsx
frontend/src/features/courses/{NoteDialog,CourseNotes,CoursesPage.test}.tsx
frontend/src/styles.css
e2e/tests/calendar-assistant.spec.ts
README.md
```

## Last full verification recorded

The latest implementation handoff recorded:

```text
make test
  Backend: 121 passed
  Frontend: 49 passed

make e2e
  Playwright/accessibility: 9 passed

make lint: passed
Frontend production build: passed
git diff --check: passed
Alembic current: 20260831_0018 (head)
Legacy completed bullets without IDs: 0
Backend health: passed
Frontend HTTP check: passed
```

Ordinary tests mock Codex. Real Codex features require private ChatGPT sign-in
from Assistant or the optional configured API-key fallback.

## Planned milestone sequence

- [x] M14 — PostgreSQL, uploads, configuration, and Docker volumes are safe
  across supported `mv`, rebuild, migration, backup, and restore workflows.
- [x] M15 — Stream uploaded PDFs safely by source ID, show them inside Teacher
  Assistant, and allow a separate browser window/tab.
- [x] M16 — Add a lightweight Markdown-aware note editor where syntax markers
  remain visible while their content is styled, plus safe Markdown rendering.
- [x] M17 — Start every note and nested summary minimized on each Notes-page
  visit, allow independent expansion, and persistently remove individual
  generated bullets without touching source notes or slides.
- [ ] M18 — Add a Codex Prettify suggestion workflow with isolated context,
  strict validation, before/after preview, explicit acceptance, and no automatic
  note save.
- [ ] M19 — Persist selected pages/views and per-conversation Assistant drafts
  in validated browser storage without caching authoritative backend data.
- [ ] M20 — Add private integration credential storage and connect one Canvas
  installation through institution-approved OAuth or a manual API-token
  fallback, without importing course content yet.
- [ ] M21 — Add Inbox and synchronize read-only Canvas announcements through
  the connected API or a per-course announcement feed.
- [ ] M22 — Ingest owner-forwarded email from a dedicated TLS/read-only IMAP
  mailbox into Inbox, with safe MIME rendering and private attachments.

The full scope, boundaries, checklist, acceptance criteria, and expected files
are in the corresponding milestone files. Do not combine or automatically
advance them.

## Known limitations and cautions

- M18–M22 are plans only and none of their application behavior exists yet.
  M19 must not persist or restore M17 note/summary expansion state.
- Canvas OAuth requires an institution-enabled developer key; a self-hosted
  clone cannot manufacture one. M20 therefore includes a manual Canvas API-token
  fallback, and M21/M22 include feed/email alternatives. Password/cookie-based
  Canvas scraping is intentionally excluded.
- Teacher Assistant cannot create a receiving email address or forwarding rule.
  M22 requires the owner to provision a dedicated IMAP mailbox and configure
  forwarding with the external mail provider.
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
- Automatic LMS course creation/import, assignments, grades, people, files,
  submissions, Study Plan, outbound mail, and provider-specific mail OAuth remain
  out of scope. M20–M22 authorize only the connection and read-only Inbox scope
  in their milestone files.

## Next step

M17 is complete. Stop before M18. The owner must explicitly select M18 before
Codex note-prettify implementation begins.

Recommended next prompt:

```text
Read AGENTS.md, instructions.md, handoff.md, and
milestones/m18-codex-note-prettify.md. Implement M18 only
and stop after its acceptance criteria are verified.
```
