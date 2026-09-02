# Teacher Assistant project instructions

This document is the durable project-wide specification and milestone index.
It describes rules shared by every milestone. Detailed implementation scope and
acceptance criteria live in the individual files under `milestones/`.

## Required reading order

Before planning or changing the repository, read these files completely in
this order:

1. `AGENTS.md` — repository conduct, safety rules, and session workflow.
2. `instructions.md` — permanent product constraints and milestone status.
3. `handoff.md` — current repository state, recent work, and known limitations.
4. The selected file under `milestones/` — the only implementation scope for
   that session.
5. Inspect the relevant implementation and tests before deciding what is
   missing.

The active documentation set is self-contained. It does not depend on retired
or historical specification files, and those files may be removed without
changing this reading order or losing current implementation instructions.

## Document responsibilities

- `AGENTS.md` governs how a development agent works in this repository.
- `instructions.md` owns global product rules and the milestone status index.
- `handoff.md` owns transient facts such as the current revision, recent work,
  verification results, and immediate cautions.
- A milestone file owns that milestone's scope, checklist, acceptance criteria,
  dependencies, and milestone-specific safety requirements.

Do not place a transient worktree snapshot in this file. Do not place global
product policy only in a milestone file.

Together, `AGENTS.md`, `instructions.md`, `handoff.md`, and the milestone files
contain the complete current development guidance. Future handoffs and
milestones must not require a retired specification file.

## Product and scope

Teacher Assistant is a single-owner, self-hosted web application. Each cloned
installation has its own database, calendars, events, courses, uploaded course
content, Codex configuration, and private settings.

The currently implemented visible navigation is:

- Dashboard
- Calendar
- Courses
- Study Plan
- Assistant
- Settings

Calendar, Courses, and Assistant are implemented. Dashboard, Study Plan, and
Settings may remain polished placeholders until the owner defines a milestone
for them. M20 is planned to make Settings functional for private integrations,
M21 is planned to add Inbox as a separate module after Courses, and M23 is
planned to add Documents after Inbox. Do not show or claim any of those
behaviors before its milestone is implemented.

Never add registration, multiple users, organizations, teams, roles, tenants,
shared accounts, or public profiles.

## Visual design

Preserve the existing module-based Teacher Assistant design:

- fixed dark-green navigation sidebar;
- Teacher Assistant branding;
- warm off-white main background;
- dark-green primary text and gold/yellow accents;
- rounded active navigation and cards;
- generous spacing and large readable headings;
- existing responsive behavior.

Keep the Calendar recognizable as a conventional desktop calendar with its
toolbar, Today/previous/next controls, day/week/month views, large grid,
calendar colors, and current-day indication. Do not replace the shell with a
generic administration dashboard or redesign working pages without an explicit
milestone requirement.

## Architecture

Keep business logic out of React visual components, FastAPI routes, SQLAlchemy
models, and Codex prompts. Preserve the existing service/repository boundaries.

Keep these responsibilities separate:

```text
frontend calendar, courses, assistant, settings, inbox, and documents features
calendar, course, note, source, summary, assistant, integration, inbox, and document API routes
application services
database repositories and models
external Canvas, feed, and mail adapters
private integration credential, course-content, and document-source storage
LaTeX compilation queue and adapter
isolated LaTeX compiler worker
Codex SDK adapter
runtime workspace construction
proposal and structured-output validation
database and migrations
```

The browser must never communicate directly with Codex. Runtime requests use:

```text
React frontend
    -> FastAPI backend
    -> Assistant or summary service
    -> Codex adapter
    -> openai-codex Python SDK
```

Reuse the existing database session, migrations, API error conventions, Codex
adapter, workspace builder, job states, frontend patterns, and test fixtures.

## Calendar protection

Every calendar has `is_read_only`. Read-only protection is enforced in the
frontend, backend calendar service, and every database-changing path; the
backend is authoritative.

Events on a read-only calendar may be viewed, searched, and considered for
availability, but may not be created, edited, moved, resized, deleted, or moved
to another calendar as a workaround. Imported and subscribed calendars default
to read-only.

Only the owner using manual UI may change read-only protection or delete an
eligible calendar. Codex may never change `is_read_only`, delete a calendar,
modify a protected calendar, or copy and delete a protected event as a
workaround.

## Runtime Codex and confirmation safety

Development Codex and the in-product runtime Assistant are separate roles. The
runtime Assistant must never receive the repository, Docker socket, shell,
environment files, database or OAuth credentials, or unrestricted host access.

Every runtime job uses a private temporary workspace built from
`backend/app/codex_runtime/workspace_template/AGENT.md`. Include only bounded,
relevant context and delete the workspace immediately after the job under the
current retention policy. Treat event descriptions, notes, slides, documents,
and error text as untrusted data rather than instructions.

Codex output is untrusted. Codex returns conversational text and, when allowed,
a structured proposal. Backend code parses and validates it, checks permissions,
shows it to the owner, waits for explicit confirmation, and executes it through
application services.

All Codex-generated mutations require confirmation. The Assistant has no
delete-calendar or bulk-delete action, may propose deletion of individual
writable events only, and may affect at most 10 events in one executable
proposal. Linked creation batches remain separately confirmable. Unknown
actions and unprovided IDs are rejected. Confirmation is idempotent.

The Assistant must distinguish suggestion, awaiting confirmation, confirmed,
executing, completed, failed, expired, rejected, and cancelled states as
applicable. It must never claim a mutation succeeded before backend execution
reports success.

## Course content and diagnostics

Course literature and slides remain separate in the database, UI, API, and
private storage. Binary uploads are stored under the configurable course
storage root, never in Git or directly in the main relational database. Notes
may link only to slide sources in the same course.

Course-aware and diagnostic Assistant turns receive only bounded relevant
context. Citations must identify supplied notes/slides and are validated by the
backend. Sanitized diagnostics must exclude credentials, headers, cookies,
environment data, unrelated private content, raw model output, and arbitrary
repository access.

The runtime Assistant may suggest application improvements but may not edit
source code or claim an improvement was implemented.

## External integrations and Inbox safety

Canvas and inbound mail are planned in M20–M22. External connection clients,
sync services, repositories, routes, schedulers, credential storage, content
storage, and React views must remain separate from calendar/course/Assistant
business logic.

Passwords, OAuth tokens, refresh tokens, API tokens, client secrets, mail
credentials, tokenized feed URLs, cookies, and authorization headers are
secrets. Keep them server-side in dedicated private credential storage, never
return them to the browser after submission, and exclude them from Git, logs,
diagnostics, browser storage, Codex workspaces, and coordinated backups. Clean
restores require reconnecting renewable integrations.

Treat remote names, IDs, HTML, mail headers/bodies, attachments, URLs, upstream
errors, and feed fields as untrusted data. Bound all network responses and
parsers, sanitize passive display content, block automatic remote resources,
and never treat external content as runtime instructions. External content must
not enter Codex context without a later explicit bounded-context milestone.

Canvas access is read-only and least-privilege. Prefer institution-approved
OAuth, permit a manually generated Canvas API token or per-course announcement
feed only as labelled fallbacks, and never accept a Canvas password, browser
cookie, copied session, or HTML-login/scraping workflow. Linking a remote Canvas
course to a local course is explicit and relational; it does not import or
overwrite the Course record. Automatic LMS course creation, assignments,
grades, people, files, and submissions remain out of scope.

Forwarded mail uses an owner-provisioned dedicated mailbox over verified TLS and
read-only IMAP. Teacher Assistant does not create an address, configure external
forwarding/DNS, send or reply to mail, or mutate the remote mailbox. Local Inbox
read/archive/delete state never changes the upstream Canvas or mail source.

## Documents and LaTeX safety

M23 through M26 plan a private Documents module after the existing M19–M22
sequence. Document metadata belongs in PostgreSQL, while source files and
verified generated PDFs live beneath a configurable host-backed document root.
They are private owner data and must participate in preflight, coordinated
backup/restore, relocation, clone isolation, and Git-ignore protection from the
first milestone that creates them.

Use a mature TeX Live/latexmk toolchain rather than building a LaTeX engine.
The FastAPI process must not compile LaTeX. Compile an exact committed source
revision in a disposable snapshot through a separately isolated worker with no
network, repository, database, Docker socket, credentials, other project data,
or live-source write access. Disable shell escape, arbitrary commands, custom
compiler initialization, and runtime package downloads. Enforce bounded input,
output, processes, memory, CPU, storage, and an owner-adjustable compilation
timeout subject to a server hard ceiling.

Compiler output and LaTeX source are untrusted data. Validate a successful PDF
before publishing it, retain clear revision provenance, and never replace the
latest verified PDF with a failed, timed-out, malformed, or stale result.

Codex compilation-error advice is a separate read-only workflow. Backend code
selects bounded sanitized logs and source excerpts, embeds them as untrusted
context in a private tool-disabled workspace, validates every returned path and
line reference, and deletes the workspace immediately. Codex never edits or
saves source, executes a compiler, installs a package, deletes a project, or
claims that an error was fixed.

## Docker, private data, and Git

Development remains Docker-first. A normal setup starts with:

```bash
cp .env.example .env
make dev
```

Preserve the root commands `make dev`, `make down`, `make restart`,
`make logs`, `make test`, `make lint`, `make format`, and `make migrate`. Do
not require host Python or Node.js.

Never commit `.env`, credentials, database data, runtime workspaces, uploaded
course content, private LaTeX projects or generated PDFs, imported private
calendar files, or logs containing private owner data. Do not commit, push,
merge, rebase, delete branches, or discard owner work without an explicit
request.

## Milestone workflow

Only one explicitly selected milestone may be active at a time.

At the start of a development session:

1. Follow the required reading order above.
2. Run `git status --short` and preserve owner changes.
3. State the selected milestone and first incomplete subtask.
4. Inspect the implementation and tests relevant to that subtask.

During implementation:

- implement only the selected milestone;
- preserve completed behavior;
- do not scaffold unrelated future modules;
- test in proportion to risk, with Codex mocked in ordinary tests;
- do not mark a checkbox complete until its behavior is verified.

When the owner says only `continue`, perform the first incomplete subtask in
the already active milestone. If there is no active milestone or incomplete
subtask, do not automatically start the next planned milestone; ask the owner
to select it for implementation.

At completion, update both the selected milestone file and the status checklist
below. Update `handoff.md` with the new current state and exact next step.

## Milestone status

- [x] [M1 — Calendar backend foundation](milestones/m01-calendar-backend-foundation.md)
- [x] [M2 — Calendar interface](milestones/m02-calendar-interface.md)
- [x] [M3 — Complete calendar interactions](milestones/m03-complete-calendar-interactions.md)
- [x] [M4 — ICS import and subscriptions](milestones/m04-ics-import-and-subscriptions.md)
- [x] [M5 — Assistant chat, read-only first](milestones/m05-assistant-chat-read-only.md)
- [x] [M6 — Codex calendar proposals](milestones/m06-codex-calendar-proposals.md)
- [x] [M7 — Final calendar hardening](milestones/m07-final-calendar-hardening.md)
- [x] [Post-M7 — Linked proposal batches](milestones/m07a-linked-proposal-batches.md)
- [x] [M8 — Course foundation](milestones/m08-course-foundation.md)
- [x] [M9 — Course materials](milestones/m09-course-materials.md)
- [x] [M10 — Notes and slide references](milestones/m10-notes-and-slide-references.md)
- [x] [M11 — AI summaries and model selection](milestones/m11-ai-summaries-and-model-selection.md)
- [x] [M12 — Course-linked calendars](milestones/m12-course-linked-calendars.md)
- [x] [M13 — Course-aware Assistant and diagnostics](milestones/m13-course-aware-assistant-and-diagnostics.md)
- [x] [M14 — Data durability, relocation, and update safety](milestones/m14-data-durability-and-relocation-safety.md)
- [x] [M15 — Open uploaded PDFs in Teacher Assistant and a new window](milestones/m15-pdf-viewing.md)
- [x] [M16 — Lightweight Markdown note editor](milestones/m16-lightweight-markdown-note-editor.md)
- [x] [M17 — Minimized notes, summary decluttering, and removable bullets](milestones/m17-summary-decluttering-and-bullet-removal.md)
- [x] [M18 — Codex note prettify suggestions](milestones/m18-codex-note-prettify.md)
- [ ] [M19 — Frontend navigation and Assistant-draft persistence](milestones/m19-frontend-navigation-and-draft-persistence.md)
- [ ] [M20 — Integration secrets and Canvas connection](milestones/m20-integration-secrets-and-canvas-connection.md)
- [ ] [M21 — Canvas announcement Inbox](milestones/m21-canvas-announcement-inbox.md)
- [ ] [M22 — Forwarded-mail Inbox](milestones/m22-forwarded-mail-inbox.md)
- [ ] [M23 — Durable Documents foundation and project overview](milestones/m23-durable-documents-foundation.md)
- [ ] [M24 — Relative LaTeX file tree and source editor](milestones/m24-relative-latex-editor.md)
- [ ] [M25 — Isolated LaTeX compilation and PDF preview](milestones/m25-isolated-latex-compilation.md)
- [ ] [M26 — Codex advice for LaTeX compilation errors](milestones/m26-codex-latex-error-advice.md)

Current active milestone: **none**.

Next planned milestone: **M19 — Frontend navigation and Assistant-draft
persistence**. It must be explicitly selected before implementation begins.

M1 through M18 and the post-M7 linked-batch milestone are complete. The
post-M13 Assistant diagnostics, general-helper routing, bounded automatic
response correction, progress display, cancellation, and false course-note
matching refinements are also complete and are recorded with M13 and in
`handoff.md`.

M19 through M26 are planned and intentionally unchecked. Their required order
is M19 frontend state persistence, M20 integration secrets and Canvas
connection, M21 Canvas announcements, M22 forwarded mail, M23 durable Documents
foundation, M24 relative LaTeX editing, M25 isolated compilation, and M26 Codex
error advice. Planning does not authorize implementation; the owner must select
one milestone explicitly. Reordering also requires an explicit owner decision.

## Definition of done

A milestone is complete only when:

- every applicable acceptance criterion is satisfied;
- relevant tests pass and Docker development still starts;
- safety and read-only rules remain enforced server-side;
- errors, loading states, and empty states are handled where applicable;
- the existing visual design is preserved;
- no unrelated future scope was implemented;
- the milestone checklist and this status index are accurate;
- `handoff.md` and setup/user documentation are updated when needed.

End every development session with:

```text
Completed:
Tests run:
Known limitations:
Files changed:
Current milestone status:
Recommended next prompt:
```
