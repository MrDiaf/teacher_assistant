# Teacher Assistant development handoff

Updated: 2026-09-03

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

- Git `HEAD`: `1d5a374 milestone 19 is complete`
- M1 through M19 are complete.
- The post-M7 linked Assistant proposal-batch milestone is complete.
- The post-M13 Assistant diagnostics, general-helper routing, bounded automatic
  correction, working-state display, cancellation, and false course-note
  matching refinements are complete and committed in `a14781d`.
- M20 through M24 are planned, but no implementation milestone is active.
- The current uncommitted worktree contains only the planning-document changes
  that retire the Canvas roadmap and renumber the remaining milestones. No
  M20–M24 application code or behavior was implemented. Preserve the work
  because no commit was requested.
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
  creation batches, retries, diagnostics, progress, cancellation, restored
  conversation/sidebar selection, and browser-local per-conversation drafts.
- Courses: manual CRUD/archive/restore, private Literature and Slides storage,
  extraction, in-app and new-window PDF viewing, notes and slide references, AI
  summaries with provenance, Codex note-prettify suggestions, course-linked
  calendars, and course-aware Assistant answers.
- Navigation convenience state restores the active module, main/per-course
  Calendar view and anchor, and selected course/tab without caching API data.
- Dashboard and Study Plan remain placeholder modules. Settings also remains a
  placeholder until the planned M20 inbound-mail work is explicitly selected
  and implemented; Inbox does not exist until M20, and Documents does not exist
  until M21.

The permanent safety and architecture rules are in `AGENTS.md` and
`instructions.md`. Do not duplicate or weaken them in a new milestone.

## Most recent planning update

The owner retired the unimplemented Canvas connection and announcement roadmap
because the required external resources are unavailable. The former M20 and M21
Canvas milestone files were removed. Forwarded-mail Inbox moved from M22 to M20
and now owns the private credential-store setup it previously depended on.

The approved Overleaf-inspired Documents/LaTeX roadmap moved forward by two
positions and remains documentation only after completed M19 and planned M20:

- M21 adds durable UUID-based document projects, colored many-to-many tags,
  project search/actions, raw `.tex`/source-ZIP downloads, and coordinated
  preflight/backup/restore before creating private document data.
- M22 adds a CodeMirror-based root-relative LaTeX file tree and source editor,
  bounded verified assets, server-backed autosave, stale-write protection, and
  a selected main `.tex` file.
- M23 adds pdfLaTeX through a pinned TeX Live/latexmk toolchain in a separate
  offline non-root compiler worker, disposable source snapshots, resource and
  process limits, a per-project 10–600-second timeout with a hard ceiling,
  revision-aware logs, validated PDF preview, and overview downloads.
- M24 adds read-only Codex advice for failed/timed-out compilations using only
  bounded sanitized logs and relevant source excerpts. Codex cannot edit,
  compile, install, delete, or claim a fix was applied.

The detailed scope, boundaries, checklists, acceptance criteria, and expected
implementation areas are in `milestones/m21-durable-documents-foundation.md`
through `milestones/m24-codex-latex-error-advice.md`. Those four milestones and
M20 remain unchecked. No application source, migration, dependency, Compose,
environment, README, or runtime behavior was changed by this planning update.

## Most recent completed work

M19 frontend navigation and Assistant-draft persistence:

- adds one typed, versioned `teacher-assistant.ui-state.v1` browser-storage
  boundary that validates allowed module/view/tab values, UUIDs, real local
  dates, timestamps, text size, and record counts;
- restores the active module, main and course-scoped Calendar view/anchor, and
  selected existing course/tab before their first relevant render;
- reloads authoritative calendars, events, courses, notes, conversations,
  proposals, activity, authentication, and permissions from FastAPI on every
  page mount rather than persisting those datasets;
- keeps exact Assistant drafts separately for each conversation and a local
  not-yet-created conversation, with a 4,000-character/20-draft cap that
  protects the active draft;
- creates a new backend conversation only when Send is pressed, moves only the
  matching new-conversation draft, clears it only after a successful handoff,
  and retains it on validation, auth, network, cancellation, or runtime failure;
- adds an accessible Clear draft action, stale-ID cleanup, corrupt/full/disabled
  storage fallback, and canonical sanitization that discards unknown/private
  fields;
- deliberately leaves M17 note and summary disclosures out of persistence, so
  every Notes remount/reload still starts minimized;
- includes storage/privacy/limit tests, unmount/reload and multi-conversation
  integration coverage, course-scoped Calendar tests, and a Playwright
  navigation/reload/accessibility scenario.

Important M19 implementation areas:

```text
frontend/src/persistence/uiState.ts
frontend/src/App.tsx
frontend/src/features/calendar/CalendarPage.tsx
frontend/src/features/courses/{CoursesPage,CourseCalendar}.tsx
frontend/src/features/assistant/AssistantPage.tsx
frontend/src/features/assistant/api.ts
frontend/src/App.persistence.test.tsx
frontend/src/styles.css
frontend tests and e2e/tests/calendar-assistant.spec.ts
README.md
```

M18 Codex note-prettify suggestions:

- adds a visually secondary Prettify action beside the Markdown editor and
  reuses the installation's shared, server-authoritative AI model selector;
- sends only the current unsaved note body to a dedicated private runtime
  workspace with a correction-only policy and strict proposed-body schema;
- limits Prettify input to 40,000 characters without truncation and rejects
  invalid UTF-8, malformed output, extra fields, changed Markdown structure,
  line structure, code, links, URLs, formulas, citations, or quoted text;
- deletes every temporary workspace immediately and never persists model output,
  a rejected suggestion, hidden reasoning, or any note mutation;
- shows the complete original and proposed Markdown in an accessible comparison,
  with explicit Keep and Use actions and focus returned to the editor;
- replaces only the local draft after acceptance, keeps Create/Save separate,
  and preserves the draft through rejection, close, cancellation, timeout,
  invalid model, oversized input, runtime failure, and no-change responses;
- includes backend privacy/prompt-injection/validation tests, frontend interaction
  and cancellation tests, and an accessible Playwright owner workflow.

Important M18 implementation areas:

```text
backend/app/notes/prettify_{routes,schemas,service}.py
backend/app/codex_runtime/workspace.py
backend/app/codex_runtime/workspace_template/PRETTIFY_AGENT.md
backend/tests/test_note_prettify.py
frontend/src/features/courses/{NoteDialog,MarkdownNoteEditor}.tsx
frontend/src/features/courses/NoteDialog.test.tsx
frontend/src/features/courses/{api,types}.ts
frontend/src/styles.css
e2e/tests/calendar-assistant.spec.ts
README.md
```

## Earlier completed work

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
  Backend: 142 passed
  Frontend: 65 passed

make e2e
  Playwright/accessibility: 10 passed

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
- [x] M18 — Add a Codex Prettify suggestion workflow with isolated context,
  strict validation, before/after preview, explicit acceptance, and no automatic
  note save.
- [x] M19 — Persist selected pages/views and per-conversation Assistant drafts
  in validated browser storage without caching authoritative backend data.
- [ ] M20 — Add Inbox and ingest owner-forwarded email from a dedicated
  TLS/read-only IMAP mailbox, with private credential storage, safe MIME
  rendering, and private attachments.
- [ ] M21 — Add durable private LaTeX projects, searchable/tagged overview,
  source downloads, and coordinated document backup/restore.
- [ ] M22 — Add the root-relative multi-file LaTeX tree and CodeMirror source
  editor with safe assets, autosave, and stale-write protection.
- [ ] M23 — Add isolated TeX Live/latexmk compilation, adjustable timeouts,
  bounded logs, validated PDF preview, and overview PDF downloads.
- [ ] M24 — Add bounded read-only Codex advice for failed and timed-out LaTeX
  compilations without automatic source changes.

The full scope, boundaries, checklist, acceptance criteria, and expected files
are in the corresponding milestone files. Do not combine or automatically
advance them.

## Known limitations and cautions

- M20–M24 are plans only and none of their application behavior exists yet.
- M19 convenience state is browser-profile/origin specific. Clearing site data,
  using another browser/device, or private browsing removes preferences and
  unsent drafts but does not delete backend records. Cross-device sync and
  offline API caching remain intentionally out of scope.
- Documents intentionally has no sharing, collaboration, public links, visual
  editor, version history, arbitrary build commands, shell escape, runtime
  package downloads, automatic Codex fixes, or additional compiler engines in
  M21–M24. The initial M23 compiler is pdfLaTeX through TeX Live/latexmk.
- Teacher Assistant cannot create a receiving email address or forwarding rule.
  M20 requires the owner to provision a dedicated IMAP mailbox and configure
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
  out of scope. M20 authorizes only the dedicated inbound-mail connection and
  local Inbox scope defined in its milestone file.

## Next step

M19 is complete, and the M21–M24 Documents roadmap remains planning only. Stop
before M20. The owner must explicitly select M20 before forwarded-mail Inbox
implementation begins. Do not skip to M21 or reorder the roadmap without
another explicit owner decision.

Recommended next prompt:

```text
Read AGENTS.md, instructions.md, handoff.md, and
milestones/m20-forwarded-mail-inbox.md. Implement M20 only
and stop after its acceptance criteria are verified.
```
