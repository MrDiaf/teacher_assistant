# Teacher Assistant project instructions

This document is the durable project-wide product specification. It describes
the product rules shared by every milestone. It does not describe how work is
carried out or which milestone is current.

## Where everything else lives

The working method is defined by the files under `guidelines/`. The reading
order for a development session is in `AGENTS.md`, section 3.

- `AGENTS.md` holds the project-specific conduct and safety rules and points to
  the guidelines.
- `guidelines/` owns the working method: general approach, scope, planning and
  milestones, development environment, and deployment.
- `PLAN.md` owns milestone order, dependencies, and checkbox status.
- A file under `guidelines/milestones/` owns one open milestone's objective,
  dependencies, scope, required work, completion criteria, verification, and
  milestone-specific safety requirements.
- `instructions.md` owns the global product rules below.
- `handoff.md` owns transient facts such as the current revision, recent work,
  verification results, and immediate cautions.
- `docs/modules/README.md` indexes module README/handoff pairs created by M21A.
  Each README owns scope, interfaces, paths, and working commands; each local
  handoff owns current work and verification. Root handoff links local state
  and retains shared cautions instead of repeating every module's history.
- `legacy/` is archived history from the retired workflow, including the
  completed milestone files. It is never guidance. `AGENTS.md` opens with a
  document map marking every path as active or legacy.

Do not place a transient worktree snapshot or milestone status in this file. Do
not place global product policy only in a milestone file.

The active documentation set is self-contained. It does not depend on the
archived milestone files, and those files may be removed without losing current
instructions.

## Product and scope

Teacher Assistant is a single-owner, self-hosted web application. Each cloned
installation has its own database, calendars, events, courses, uploaded course
content, Codex configuration, and private settings.

The currently implemented visible navigation is:

- Dashboard
- Calendar
- Courses
- Inbox
- Documents
- Study Plan
- Assistant
- Settings

Calendar, Courses, Inbox, Documents, Assistant, and the mail-integration area
of Settings are implemented. Dashboard and Study Plan may remain polished
placeholders. Documents currently provides the M21 project overview and
durable source foundation; editing, compilation, preview, and Codex advice
remain later milestones.

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
external mail adapters
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

### Approved modular refactoring target

The owner selected a refactoring roadmap before further feature development.
M21A-M21I incrementally establish the following target; planning does not imply
these boundaries, module switches, or focused commands are implemented yet.

- Keep one repository, React application shell, FastAPI application, and
  PostgreSQL installation. Separate deployment is reserved for a justified
  isolation requirement such as the planned M23 compiler worker.
- Calendar, Courses, Assistant, Inbox, and Documents own their feature code,
  styles, business data, storage behavior, and tests. Courses includes notes,
  materials, summaries/prettify, and course-calendar associations. Inbox owns
  mail connections and its Settings contribution. Dashboard/Study Plan remain
  shell-owned placeholders, not new services or features.
- A small platform owns composition/navigation, the Settings host, shared UI
  primitives, configuration, database sessions, migration/backup coordination,
  shared AI runtime, and sanitized diagnostics. Business logic does not migrate
  into a catch-all shared service or global registry.
- Use explicit typed public interfaces and declared acyclic dependencies.
  Feature code may not import another owner's internal components, repositories,
  ORM entities, or query its tables directly. Public contracts return bounded
  data and errors, not raw sessions, SQL, credentials, or physical server paths.
  Permission checks remain within the authoritative owning service.
- Keep foreign-key protection and centrally ordered migrations. Document an
  application transaction coordinator where operations must be atomic across
  owners; modularity must not introduce partial commits or remove data integrity.
  Preserve existing APIs, IDs, migration history, storage identities, backup
  formats, private data, and supported UI behavior through each transition.
- Assemble bundled modules through a small code-owned registration contract.
  The shared development/test host uses the same module and shell entries as
  production. Reuse Docker images and common Compose configuration; profiles
  select services, while application configuration selects modules. No host
  Python/Node requirement, copied mock website, or arbitrary plugin loader.
- M21H adds owner-controlled enable/disable for bundled features, with backend
  route/service/job enforcement and explicit dependency effects. Disabling
  retains all data, drafts, and credentials and leaves migration/backup/recovery
  available. Uninstall, data purge, package downloads, and Docker control through
  Settings remain out of scope. Shared AI is independent of Assistant UI state.
- Test boundaries, modules, provider/consumer contracts, real integrations, and
  the assembled application separately. Focused checks never substitute for
  affected-consumer checks or required final regression/recovery verification.
  Isolate test databases/storage and measure build/setup and execution costs.

M21A inventories existing violations with exact removal milestones; each later
milestone removes its allowances. Do not silently broaden that inventory to
permit new coupling. M21I requires no remaining legacy boundary exceptions.
Module boundaries govern maintainability, not process security isolation;
runtime Codex and the future compiler retain their separate enforced sandboxes.
Refactoring proceeds one verified milestone/subtask at a time, with the
Documents pilot before the other feature migrations. It does not authorize a
whole-project rewrite in one session or implementation of M22-M24 features.

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

## External mail and Inbox safety

Inbound mail is implemented in M20. Mail connection clients, sync services,
repositories, routes, schedulers, credential storage, attachment storage, and
React views must remain separate from calendar/course/Assistant business logic.

Passwords, app passwords, provider tokens, refresh tokens, mail credentials,
cookies, and authorization headers are secrets. Keep them server-side in
dedicated private credential storage, never return them to the browser after
submission, and exclude them from Git, logs, diagnostics, browser storage,
Codex workspaces, and coordinated backups. Clean restores require reconnecting
renewable integrations.

Treat remote names, IDs, HTML, mail headers/bodies, attachments, URLs, and
upstream errors as untrusted data. Bound all network responses and parsers,
sanitize passive display content, block automatic remote resources, and never
treat external content as runtime instructions. External content must not enter
Codex context without a later explicit bounded-context milestone.

Forwarded mail uses an owner-provisioned dedicated mailbox over verified TLS and
read-only IMAP. Teacher Assistant does not create an address, configure external
forwarding/DNS, send or reply to mail, or mutate the remote mailbox. Local Inbox
read/archive/delete state never changes the upstream mail source. Automatic LMS
course creation or import, assignments, grades, people, files, and submissions
remain out of scope.

## Documents and LaTeX safety

M21 establishes the private Documents module after the M20 Inbox milestone;
M22 through M24 plan its editor, compiler, and read-only advice workflows after
the M21A-M21I refactoring sequence is complete.
Document metadata belongs in PostgreSQL, while source files and
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

## Milestones and working method

How work is planned, scoped, verified, and reported is defined by the files
under `guidelines/` together with `AGENTS.md`, not by this file. Milestone
order and status are in `PLAN.md`; each open milestone is a file under
`guidelines/milestones/`.

Only one explicitly owner-selected milestone may be active at a time. Planning
a milestone does not authorize implementing it, and reordering the plan
requires an explicit owner decision.
