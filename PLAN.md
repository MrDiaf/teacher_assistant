# Plan

Top-level progress file for Teacher Assistant, as required by
[`guidelines/plan.md`](guidelines/plan.md). It holds milestone ordering,
dependencies, and the checkbox status of every milestone. Full instructions for
each open milestone live in its own file under
[`guidelines/milestones/`](guidelines/milestones/).

**Active milestone: M21G.** The owner selected M21E through M21I on 2026-09-30,
to be completed in order. M21E and M21F are complete. A milestone becomes
active only when the owner explicitly selects it.

## Rules for this file

- Each checkbox below mirrors, in the same order, one completion criterion in
  the milestone file. Update both together; they must stay synchronized.
- Check a box only after the criterion has been verified, not when code
  intended to satisfy it has been written.
- The criteria here are short labels. The milestone file holds the full wording.
- A milestone being listed here does not authorize work on it.

## Order and dependencies

```text
M21E -> M21F -> M21G -> M21H -> M21I -> M22 -> M23 -> M24
```

Each milestone requires the one before it. M21E-M21I finish the modular
refactoring of the existing modules (Courses, Assistant and AI platform,
Inbox/Settings, module controls, final verification). M22-M24 then add the
Documents LaTeX editor, isolated compilation, and Codex error advice; they must
not start before M21I is complete. Reordering requires an explicit owner
decision.

## Open milestones

### M21E — Courses ownership and Calendar integration

[Milestone file](guidelines/milestones/m21e-courses-module-boundary.md)

- [x] No other feature reaches Courses repositories, tables, or internals
- [x] Every completed Course workflow passes locally and in the full application
- [x] Literature and Slides stay distinct; note links and citations keep provenance
- [x] Removing a course or association cannot delete Calendar-owned events
- [x] Shared AI access keeps isolation, explicit acceptance, and data limits
- [x] Course files stay recoverable through coordinated backup/restore
- [x] Focused, contract, integration, accessibility, lint/build, Docker, migration, and diff checks pass

### M21F — Assistant boundary, shared AI runtime, and diagnostics

[Milestone file](guidelines/milestones/m21f-assistant-and-ai-platform.md)

- [x] Assistant mounts in the shared host with fake and real capabilities
- [x] Ordinary tests use no Codex credentials and no real model requests
- [x] Summaries/prettify work without Assistant internals; shared auth and diagnostics are independent
- [x] Runtime jobs keep their isolation; cancellation/timeout deletes workspaces
- [x] Unknown, read-only, bulk, delete-calendar, invalid, and repeated requests keep enforced behavior
- [x] Drafts survive navigation/failure; completed status follows backend execution
- [x] Focused, runtime, contract, cross-module E2E, accessibility, lint/build, Docker, migration, and diff checks pass

### M21G — Inbox ownership and contributed Settings panels

[Milestone file](guidelines/milestones/m21g-inbox-and-settings-boundary.md)

- [ ] Inbox and mailbox Settings actions pass through one real module entry in full and focused apps
- [ ] Mail credentials never return to the browser or enter logs, diagnostics, Codex, Git, or backups
- [ ] Credential, TLS/auth, malformed-mail, UIDVALIDITY, race, and cleanup failures stay recoverable
- [ ] Local read/archive/delete never modifies the remote mailbox
- [ ] Settings holds no Inbox business logic; panels stay accessible; placeholders stay placeholders
- [ ] No unscheduled legacy boundary allowance remains for migrated features
- [ ] Focused, contract, smoke, accessibility, lint/build, Docker, backup/restore, and diff checks pass

### M21H — Module controls and data-preserving lifecycle

[Milestone file](guidelines/milestones/m21h-module-controls-and-lifecycle.md)

- [ ] All-enabled upgrade is unchanged; each feature disables/re-enables independently
- [ ] Routes, integrations, stale proposals, and jobs cannot use a disabled feature
- [ ] Disabling Inbox or Calendar stops polling/subscriptions without deleting data
- [ ] Jobs, confirmations, saves/imports, and concurrent toggles resolve consistently
- [ ] IDs, hashes, settings, and drafts survive disable/re-enable and backup/clean restore
- [ ] Focused, lifecycle, contract, combination E2E, accessibility, lint/build, Docker, recovery, and diff checks pass

### M21I — Modular verification, Docker workflow, and refactoring completion

[Milestone file](guidelines/milestones/m21i-modular-verification-and-cutover.md)

- [ ] Every module mounts through the same entry in the real app and focused host
- [ ] Feature styles are owned locally; global CSS holds only shared primitives/shell rules
- [ ] No business module bypasses another module's public interface
- [ ] Module-local iteration needs no shell or root CSS edits; contract changes select consumers
- [ ] Measurements show a shorter warm focused loop than full verification
- [ ] All-enabled and disabled-module configurations preserve data and workflows
- [ ] Full tests, contracts, architecture, E2E, lint, build, Docker, upgrade, recovery, and diff checks pass
- [ ] Root documentation is a concise current index

### M22 — Relative LaTeX file tree and source editor

[Milestone file](guidelines/milestones/m22-relative-latex-editor.md)

- [ ] Owner can build a nested source tree and edit multiple UTF-8 files in-app
- [ ] Root-relative tree paths match the paths the compiler will use
- [ ] A nested sample project keeps its relative paths through save, reopen, ZIP, backup, and restore
- [ ] Autosave reports its actual state and never claims a failed write succeeded
- [ ] A stale tab cannot silently overwrite a newer revision
- [ ] Invalid paths, unsupported files, spoofed images, symlinks, and quota overflows fail safely
- [ ] The main-document selection always names an existing `.tex` file
- [ ] Keyboard and screen-reader users can navigate, open, edit, save, and recover
- [ ] Existing Documents overview, backup, deletion, and earlier modules stay intact
- [ ] Backend, frontend, storage, E2E, lint, build, Docker, and diff checks pass

### M23 — Isolated LaTeX compilation and PDF preview

[Milestone file](guidelines/milestones/m23-isolated-latex-compilation.md)

- [ ] A multi-file project with a chapter, bibliography, and image compiles to a readable PDF
- [ ] Owner can change the project timeout; the effective value shows on each job
- [ ] A long compile is killed at the deadline with its children and becomes `timed_out`
- [ ] A LaTeX error becomes `failed` with a bounded root-relative log
- [ ] Shell escape, custom config, network, path, process, and output abuse fail inside the sandbox
- [ ] Successful PDFs can be previewed, opened separately, and downloaded with safe ranges
- [ ] A later failure keeps the prior verified PDF, labelled older; stale results are never shown as current
- [ ] Compiler restarts and abandoned jobs resolve safely and disposable files are cleaned
- [ ] Ordinary tests need no Codex credential or network; one containerized test uses the real compiler
- [ ] Existing Documents source integrity and earlier modules stay intact
- [ ] Tests, compiler integration, Docker, migrations, lint, build, E2E, security, and diff checks pass

### M24 — Codex advice for LaTeX compilation errors

[Milestone file](guidelines/milestones/m24-codex-latex-error-advice.md)

- [ ] A known missing-file or syntax error gets a readable explanation, causes, and steps
- [ ] Every returned file reference exists in the failed job's exact revision with a valid line range
- [ ] Source/log prompt injection cannot expand context, call tools, or weaken validation
- [ ] Codex receives no images, PDFs, other projects, credentials, or unrelated private content
- [ ] Advice requests leave source, metadata, compile history, and the latest PDF byte-for-byte unchanged
- [ ] The UI never claims an error was fixed or a document recompiled
- [ ] Invalid, oversized, malformed, unauthenticated, and failed responses fail safely with no stored raw output
- [ ] The temporary workspace is deleted on every terminal path
- [ ] Ordinary tests use a mocked Codex adapter and no real credentials
- [ ] Existing Assistant, Prettify, compiler isolation, Documents editing, and earlier modules stay intact
- [ ] Backend, runtime, frontend, privacy, accessibility, E2E, lint, build, Docker, and diff checks pass

## Completed milestones (legacy archive)

M1 through M21D were completed under the project's earlier workflow. Their
files are kept in [`legacy/milestones/`](legacy/milestones/) as historical context only; the
repository is the source of truth for what they implemented.

- [x] [M1 — Calendar backend foundation](legacy/milestones/m01-calendar-backend-foundation.md)
- [x] [M2 — Calendar interface](legacy/milestones/m02-calendar-interface.md)
- [x] [M3 — Complete calendar interactions](legacy/milestones/m03-complete-calendar-interactions.md)
- [x] [M4 — ICS import and subscriptions](legacy/milestones/m04-ics-import-and-subscriptions.md)
- [x] [M5 — Assistant chat, read-only first](legacy/milestones/m05-assistant-chat-read-only.md)
- [x] [M6 — Codex calendar proposals](legacy/milestones/m06-codex-calendar-proposals.md)
- [x] [M7 — Final calendar hardening](legacy/milestones/m07-final-calendar-hardening.md)
- [x] [Post-M7 — Linked proposal batches](legacy/milestones/m07a-linked-proposal-batches.md)
- [x] [M8 — Course foundation](legacy/milestones/m08-course-foundation.md)
- [x] [M9 — Course materials](legacy/milestones/m09-course-materials.md)
- [x] [M10 — Notes and slide references](legacy/milestones/m10-notes-and-slide-references.md)
- [x] [M11 — AI summaries and model selection](legacy/milestones/m11-ai-summaries-and-model-selection.md)
- [x] [M12 — Course-linked calendars](legacy/milestones/m12-course-linked-calendars.md)
- [x] [M13 — Course-aware Assistant and diagnostics](legacy/milestones/m13-course-aware-assistant-and-diagnostics.md)
- [x] [M14 — Data durability, relocation, and update safety](legacy/milestones/m14-data-durability-and-relocation-safety.md)
- [x] [M15 — Open uploaded PDFs in Teacher Assistant and a new window](legacy/milestones/m15-pdf-viewing.md)
- [x] [M16 — Lightweight Markdown note editor](legacy/milestones/m16-lightweight-markdown-note-editor.md)
- [x] [M17 — Minimized notes, summary decluttering, and removable bullets](legacy/milestones/m17-summary-decluttering-and-bullet-removal.md)
- [x] [M18 — Codex note prettify suggestions](legacy/milestones/m18-codex-note-prettify.md)
- [x] [M19 — Frontend navigation and Assistant-draft persistence](legacy/milestones/m19-frontend-navigation-and-draft-persistence.md)
- [x] [M20 — Forwarded-mail Inbox](legacy/milestones/m20-forwarded-mail-inbox.md)
- [x] [M21 — Durable Documents foundation and project overview](legacy/milestones/m21-durable-documents-foundation.md)
- [x] [M21A — Module ownership, contracts, and refactoring baseline](legacy/milestones/m21a-module-ownership-and-baseline.md)
- [x] [M21B — Application composition and shared platform boundaries](legacy/milestones/m21b-application-composition.md)
- [x] [M21C — Documents module and isolated development pilot](legacy/milestones/m21c-documents-module-pilot.md)
- [x] [M21D — Calendar ownership and public service contract](legacy/milestones/m21d-calendar-module-boundary.md)

The post-M13 Assistant diagnostics, general-helper routing, bounded automatic
response correction, progress display, cancellation, and false course-note
matching refinements are also complete and are recorded with M13.
