# Teacher Assistant development handoff

Updated: 2026-09-08

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

- Git `HEAD` observed for this planning session: `e62717e m21 is done`.
- M1 through M21 are complete.
- The post-M7 linked Assistant proposal-batch milestone is complete.
- The post-M13 Assistant diagnostics, general-helper routing, bounded automatic
  correction, working-state display, cancellation, and false course-note
  matching refinements are complete and committed in `a14781d`.
- M21A-M21I are newly planned refactoring milestones before M22-M24. No
  implementation milestone is active; the next planned milestone is M21A.
- M21 is committed. The worktree was clean at the start of this planning
  session, which changes documentation only. No implementation or commit was
  requested; recheck Git instead of treating this snapshot as live status.
- The installation now has stable identity `teacher_assistant`, resolving to
  `teacher_assistant_database-data` and
  `teacher_assistant_codex-auth-data`, and
  `teacher_assistant_integration-credential-data`. The private `.env` and ignored
  `.teacher-assistant-installation` marker were created during non-destructive
  same-namespace adoption.
- The last implementation verification reported running Docker services
  (not rechecked during this documentation-only planning session):
  - frontend: `http://localhost:5173`
  - backend: `http://localhost:8000`
  - PostgreSQL: healthy
- The last verified Alembic revision is `20260908_0021 (head)`.
  Revision `20260903_0019` is a no-op
  compatibility marker for a retired, unshipped integration revision; any old
  unused tables from that local revision were deliberately left intact.
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
- Inbox imports owner-forwarded mail from one dedicated TLS/read-only IMAP
  mailbox with local search/read/archive/delete state and private attachments.
  Settings manages that connection without returning its app password.
- Documents manages private UUID-based LaTeX projects, colored many-to-many
  tags, title search and filtering, safe source downloads, and confirmed
  deletion backed by coordinated PostgreSQL/filesystem recovery.
- Dashboard and Study Plan remain placeholder modules.

The permanent safety and architecture rules are in `AGENTS.md` and
`instructions.md`. Do not duplicate or weaken them in a new milestone.

## Most recent planning update

The owner requested a whole-project modular refactoring roadmap before further
feature development. Nine plans, M21A-M21I, are inserted after completed M21
and before M22-M24. Suffix IDs preserve existing milestone names and references.
All nine implementation checklists remain unchecked and none is active.

The target is one modular monolith with explicit ownership/public interfaces,
module-owned styles/tests/documentation, shared application assembly, and one
reusable module development/test host. Keep Docker-first development and
coordinated database/filesystem durability. A separate production application
per sidebar page, plugin downloads, code uninstall, and module-data purge are
not approved scope. The later M23 compiler remains a separately isolated worker.

M21H specifically plans Settings enable/disable controls for bundled features,
with dependency effects, backend/job enforcement, preserved data, and shared AI
available independently of Assistant UI state. These controls are not built yet.

The authoritative sequence and detailed plan links are in
[instructions.md](instructions.md#milestone-status). M21A creates the ownership
map, local README/handoff pairs, and measured baseline; later module milestones
update their own documentation and remove recorded boundary violations. Until
that migration is verified, keep using the current reading workflow and do not
claim that focused Docker commands or module isolation already exist.

The earlier Canvas integration roadmap remains retired. Inbox is completed M20;
the Documents foundation is completed M21. M22-M24 keep their feature scope and
now depend on completion of the inserted refactoring sequence.

Planning verification checked 61 local Markdown links with no missing targets,
the ordered M21A-M21I dependencies and unchecked checklists, and
`git diff --check`. No application tests or runtime operations were run in this
documentation-only session; the M21 results below remain historical evidence.

## Most recent completed work

M21 durable Documents foundation and project overview:

- adds Documents after Inbox while preserving the existing responsive shell
  and extends the validated M19 module preference;
- creates PostgreSQL document-project and colored-tag metadata with UUID
  project identity, case-normalized unique tag names, and many-to-many
  associations without owner or tenant columns;
- creates each project's valid `main.tex` beneath a private UUID-derived source
  tree using restrictive permissions, atomic replacement, and coordinated
  database/filesystem rollback;
- rejects missing or mismatched trees, symlinks, hard links, special files,
  unsafe IDs, excessive source size/count, and source ZIP traversal or duplicate
  names without exposing physical server paths;
- supports project create/search/read/rename/tag/open/delete workflows, explicit
  project-named deletion confirmation, private/no-store `main.tex`, and
  deterministic source-only ZIP downloads;
- quarantines only the exact project UUID directory before database deletion,
  restores it on transaction failure, and purges it only after commit;
- includes document source and metadata in preflight, coordinated backup,
  checksummed manifests, clean restore, rollback, relocation, corruption, and
  clone-isolation coverage while retaining format-2 M20 backup compatibility;
- deliberately excludes the multi-file editor, compilation, PDF preview, and
  Codex compilation advice reserved for M22 through M24.

Important M21 implementation areas:

```text
backend/alembic/versions/20260908_0021_durable_documents_foundation.py
backend/app/documents/
backend/tests/{test_documents,test_data_archive}.py
frontend/src/features/documents/
frontend/src/{App,styles}.tsx
compose*.yml
scripts/{data-backup,data-restore,data-safety,check-data-safety,m14-relocation-drill}.sh
README.md
docs/data-durability.md
```

M20 forwarded-mail Inbox:

- adds Inbox after Courses and turns Settings into a dedicated mailbox setup,
  test, reconnect, disconnect, manual-check, and sanitized-health page;
- stores one renewable IMAP app password behind an opaque reference in a
  separate private Docker volume, never returns it, and preserves imported mail
  when that credential is missing, corrupt, replaced, or removed;
- connects only with verified implicit TLS or STARTTLS, validates public DNS
  targets, opens IMAP read-only, and uses only UID search plus bounded
  `BODY.PEEK` fetches without changing remote flags or messages;
- serializes scheduled/manual checks, applies bounded backoff, tracks mailbox
  identity plus UIDVALIDITY/UID, and preserves local messages during conservative
  UIDVALIDITY reset reconciliation and connection/import failures;
- parses bounded RFC/MIME content, prefers plain text, reduces HTML-only mail to
  passive text, blocks active/remote content, and quarantines unsafe messages
  without retaining their raw wire content;
- stores bounded attachments at generated private paths, serves them only by
  opaque ID as downloads, explains omissions, and audits/retries failed local
  file cleanup after one-message confirmed deletion;
- extends coordinated database/course/mail backup and restore while explicitly
  excluding renewable IMAP credentials and requiring reconnect on a clean
  restore;
- includes local-fake backend, frontend, Playwright/accessibility, migration,
  privacy, malformed-input, XSS, cleanup, and relocation/restore coverage.

Important M20 implementation areas:

```text
backend/alembic/versions/20260903_00{19,20}_*.py
backend/app/integrations/
backend/app/inbox/
backend/tests/{test_mail_inbox,test_data_archive}.py
frontend/src/features/{inbox,settings}/
frontend/src/{App,styles}.tsx
compose*.yml
scripts/{data-backup,data-restore,data-safety,check-data-safety,m14-relocation-drill}.sh
README.md
docs/data-durability.md
```

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

The completed M21 verification recorded:

```text
make test
  Backend: 167 passed
  Frontend: 72 passed

make e2e
  Playwright/accessibility: 12 passed

make lint: passed
Frontend production build: passed
make data-relocation-test: passed, including exact document source hashes
git diff --check: passed
Alembic current: 20260908_0021 (head)
Backend health: passed
Frontend HTTP check: passed
```

`alembic check` reports only the known pre-existing retired integration tables
and four enum/VARCHAR length differences; it reports no Documents schema drift.

Ordinary tests mock Codex. Real Codex features require private ChatGPT sign-in
from Assistant or the optional configured API-key fallback.

## Planned milestone sequence

M1-M21 and the post-M7 batch work are complete. The status checklist is owned
by [instructions.md](instructions.md#milestone-status); this is a reading guide:

1. M21A: ownership/contracts, local documentation, and measured baseline.
2. M21B: application composition and shared platform interfaces.
3. M21C: Documents pilot and initial isolated Docker/module host workflow.
4. M21D: Calendar ownership and public service contract.
5. M21E: Courses ownership, content contracts, and Calendar integration.
6. M21F: Assistant, shared AI runtime, and diagnostics boundaries.
7. M21G: Inbox ownership and contributed Settings panels.
8. M21H: data-preserving module controls and lifecycle enforcement.
9. M21I: final focused/full verification, Docker workflow, and recovery checks.
10. M22-M24: LaTeX editor, isolated compilation, then read-only Codex advice.

Each milestone requires explicit selection and verified completion. Do not
combine the whole refactor into one session or start feature work before M21I.

## Known limitations and cautions

- M21A-M21I are plans only. Public module boundaries, scoped development/test
  commands, module-local handoffs, and Settings module controls are not yet
  implemented. Existing feature folders alone do not provide that isolation.
- M22–M24 remain plans only. Documents has no multi-file editor, compilation,
  PDF preview, or Codex compilation advice yet.
- A real mailbox-provider check was not run because no private owner credential
  was provided; IMAP/TLS/authentication behavior is verified with local fakes.
- M19 convenience state is browser-profile/origin specific. Clearing site data,
  using another browser/device, or private browsing removes preferences and
  unsent drafts but does not delete backend records. Cross-device sync and
  offline API caching remain intentionally out of scope.
- Documents intentionally has no sharing, collaboration, public links, visual
  editor, version history, arbitrary build commands, shell escape, runtime
  package downloads, automatic Codex fixes, or additional compiler engines in
  M21–M24. The initial M23 compiler is pdfLaTeX through TeX Live/latexmk.
- Teacher Assistant cannot create a receiving email address or forwarding rule.
  The owner must provision a dedicated IMAP mailbox, configure forwarding, and
  enter its app password in Settings.
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
  submissions, Study Plan, outbound mail, remote mailbox mutation, and
  provider-specific mail OAuth remain out of scope.

## Next step

M21 is complete and committed. Review the new documentation-only refactoring
roadmap, then explicitly select M21A. The first implementation subtask is its
ownership/dependency/data/contract inventory. Do not start M21B or the M22
editor automatically. The current planning request does not select a milestone
for implementation and does not authorize a commit.

Recommended next prompt:

```text
Select M21A and implement its first incomplete subtask: map module ownership,
dependencies, data, public contracts, and transaction rules. Preserve existing
behavior and private data. Do not start M21B or M22, and do not commit.
```
