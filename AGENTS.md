# AGENTS.md

## Session Canary

After reading this file at the beginning of a new development session, begin the first response with:

`Ok Overseer`

This confirms that the repository instructions were loaded.

---

# Document Map: Active vs Legacy

This file is active. It is the entry point for every development session.

| Path | Status | Use it for |
| --- | --- | --- |
| `AGENTS.md` | ACTIVE | Entry point, project-specific conduct and safety rules |
| `guidelines/*.md` | ACTIVE | The working method |
| `guidelines/milestones/` | ACTIVE | Open milestones, one file each |
| `PLAN.md` | ACTIVE | Milestone order and status |
| `instructions.md` | ACTIVE | Durable product rules |
| `handoff.md` | ACTIVE | Current state and exact next step |
| `docs/modules/` | ACTIVE | Module ownership, contracts, local handoffs |
| `README.md` | ACTIVE | What the project is and how to run it |
| `legacy/` | **LEGACY** | Nothing. Archived history only |

Rules for `legacy/`:

- Never take instructions, workflow, open work, or file formats from it.
- Exclude it when searching for requirements, milestones, or rules.
- Every file in it carries a `LEGACY — ARCHIVED MILESTONE` banner. If you are
  reading a file with that banner, you are in the wrong place for guidance.
- If it disagrees with an active file or with the code, it is wrong.
- Do not add or edit files in it.

There is no root `milestones/` folder. Where `guidelines/plan.md` says
`milestones/`, this project means `guidelines/milestones/`.

---

# 1. Project

This repository contains a single-owner, self-hosted web application called:

`Teacher Assistant`

The complete future product may contain several modules. The implemented
product scope currently includes:

1. Calendar
2. Calendar Assistant powered by Codex
3. Courses, course materials, notes, summaries, and course-linked calendars
4. Forwarded-mail Inbox and its dedicated mailbox settings
5. Durable private Documents projects and source downloads

The currently implemented visible application navigation should contain:

- Dashboard
- Calendar
- Courses
- Inbox
- Documents
- Study Plan
- Assistant
- Settings

M21 added Documents after Inbox. Its editor, compiler, and Codex advice remain
planned in M22-M24. The owner has inserted refactoring milestones M21A-M21I
before that feature work; their plans do not activate implementation.

Calendar, Courses, Inbox, Documents, Assistant, and the mail-integration area
of Settings have real functionality. Dashboard and Study Plan may display a
polished placeholder page.

Do not add a new module or product phase unless the owner explicitly defines
or selects a milestone for it. Preserve the completed Course functionality;
future automatic LMS import and assignments remain out of scope.

---

# 2. Single-Owner Application

This application is for exactly one owner per installation.

Do not introduce:

- Registration
- Multiple users
- Teams
- Organizations
- Roles
- Tenant IDs
- Shared accounts
- Public profiles

The Git repository distributes the application source code.

Each cloned installation has its own:

- Database
- Calendars
- Events
- Codex configuration
- Private settings

Private runtime data must never be committed to Git.

---

# 3. Working Method

The files under `guidelines/` define how work is done in this repository. They
are the only working method. An earlier milestone workflow has been retired; do
not follow a process described in an archived milestone file.

| File | Governs |
| --- | --- |
| `guidelines/ponytail.md` | General approach: understand before changing, simplest working solution, reuse, verified completion |
| `guidelines/scope.md` | What may be modified and how widely to test |
| `guidelines/plan.md` | Milestones, completion criteria, and `PLAN.md` |
| `guidelines/development_enviroment_rules.md` | Isolated, reversible development setup |
| `guidelines/deployment.md` | Root Makefile command interface and README |

The guidelines are general rules. This file and `instructions.md` hold the
project-specific rules: product scope, single-owner constraints, visual design,
architecture, safety, Docker-first development, and Git. Where a
project-specific rule is stricter or more specific than a guideline, the
project-specific rule applies.

Before making changes:

1. Read this file.
2. Read the files under `guidelines/`.
3. Read `instructions.md` for the durable product rules.
4. Read `PLAN.md` for milestone status and `handoff.md` for current state.
5. Read the owner-selected milestone file under `guidelines/milestones/`.
6. Perform that milestone's existing-state check: inspect the implementation
   and tests and evaluate every completion criterion before changing anything.
7. State which milestone you will work on and which criteria remain unmet.

Do not read other milestone files, past or future, unless completing the
current milestone genuinely requires it. The repository is the source of truth
for what earlier milestones implemented.

Use `docs/modules/README.md` as the ownership map. Read the selected module's
README/handoff and the public contracts of relevant dependencies. Do not read
or duplicate every module's history for local work.

If no milestone is active, do not infer one from old specifications, known
limitations, or future-looking notes. Wait for the owner to define or select
the next milestone.

Do not assume something is missing without inspecting the repository.

Do not redesign working pages merely because another design is possible.

---

# 4. Milestones

Milestones are planned, stored, and executed according to `guidelines/plan.md`:

- `PLAN.md` at the repository root is the top-level progress file. It lists
  milestone order, dependencies, and the checkbox status of every milestone.
- Each open milestone is one file under `guidelines/milestones/` in the
  guidelines format: objective, dependencies, existing-state check, scope,
  required work, completion criteria, and verification.
- `legacy/milestones/` is a read-only archive of milestones completed under
  the retired workflow. It is not guidance; see the document map above.
- A new milestone is created only when the owner defines it. Write it as a new
  file under `guidelines/milestones/` and add its criteria to `PLAN.md`.

When the owner selects a milestone:

- Implement only that milestone.
- Do not automatically begin the next milestone.
- Do not scaffold unrelated future features.
- Do not add placeholder backends for future modules.
- Do not check a completion criterion until it has been verified.
- Stop after the requested milestone and report the result.

When the owner says only `continue`, work on the first unmet completion
criterion of the active milestone. If there is no active milestone, ask the
owner to define or select one rather than inventing new scope.

When a completion criterion changes state, update its checkbox in the milestone
file and the corresponding checkbox in `PLAN.md` together. If work stops midway,
leave verified criteria checked and the rest unchecked. Update `handoff.md`
with the resulting current state and exact next step.

At the end of every development session, report:

```text
Completed:
Tests run:
Known limitations:
Files changed:
Current milestone status:
Recommended next prompt:
```

---

# 5. Preserve the Existing Design

The owner likes the current module-based visual design.

Preserve:

- Fixed dark-green navigation sidebar
- Teacher Assistant branding
- Warm off-white main background
- Gold/yellow accent
- Rounded active navigation item
- Large readable page headings
- Clearly separated application modules

The Calendar page should be inspired by a conventional desktop calendar:

- Top calendar toolbar
- Today button
- Previous and next navigation
- Current date-range heading
- Day, week, and month views
- Large calendar grid
- List of calendars and their colors
- Clear current-day indication

Do not replace the application shell with a generic admin dashboard.

Do not copy Google Calendar exactly. Use it only as a usability reference.

---

# 6. Docker Development

Development must remain Docker-first. This is the project's application of
`guidelines/development_enviroment_rules.md` and `guidelines/deployment.md`.

Required host tools:

- Docker
- Docker Compose
- Git
- Make
- An editor

The project should support:

```bash
cp .env.example .env
make dev
```

Use bind mounts for source code.

Do not keep the Git repository inside an ephemeral container.

Common commands should be available through the root Makefile:

```bash
make dev
make down
make restart
make logs
make test
make lint
make format
make migrate
```

Do not require Python or Node.js to be installed directly on the host.

Known gap: `guidelines/deployment.md` requires `make up` and `make help`. The
Makefile does not provide them yet; `make dev` is the current start command.
Closing this gap is not part of any milestone until the owner schedules it.

---

# 7. Architecture

Use a modular architecture. The approved M21A-M21I target is a modular monolith:
one repository, React shell, FastAPI application, and PostgreSQL installation,
with module-owned code/data/styles/tests and enforced public interfaces.
The staged boundaries and dependency rules are in `instructions.md` and the
selected refactoring milestone. Do not replace this with a service per page.

Keep these areas separate:

```text
frontend calendar feature
frontend assistant feature
calendar API routes
calendar application service
calendar database repository
assistant API routes
assistant application service
Codex SDK adapter
proposal validation
database
frontend documents feature
document API routes
document application service
document database repository
document filesystem storage
LaTeX compilation queue and adapter
isolated LaTeX compiler worker
document compilation-advice service
```

Business logic must not live directly inside:

- React visual components
- FastAPI routes
- SQLAlchemy models
- Codex prompts

Use backend services for calendar operations.

The browser must never communicate directly with Codex.

Required flow:

```text
React frontend
    ↓
FastAPI backend
    ↓
Assistant service
    ↓
Codex adapter
    ↓
openai-codex Python SDK
```

---

# 8. Calendar Protection Rules

Every calendar has an `is_read_only` property.

Read-only protection must be enforced in all three places:

1. Frontend controls
2. Backend calendar service
3. Database-changing operations

The backend is the final authority.

Never rely only on hiding a button in the frontend.

For a read-only calendar:

- Events may be viewed.
- Events may be searched.
- Events may be used when checking availability.
- Events may not be created.
- Events may not be edited.
- Events may not be moved.
- Events may not be resized.
- Events may not be deleted.

The Codex assistant must never be able to:

- Turn read-only protection off
- Modify a read-only calendar
- Move events out of a read-only calendar as a workaround
- Copy an event and then delete the original
- Delete a protected calendar

Imported or subscribed calendars should default to read-only.

---

# 9. Runtime Codex Assistant

Codex is used both as a development agent and as a feature inside the finished application.

These are separate roles.

The runtime calendar assistant must not behave as a coding agent.

It must not receive access to:

- The source repository
- The Docker socket
- A shell
- Environment files
- Database credentials
- OAuth credentials
- The complete host filesystem

The backend must create a dedicated temporary working directory for runtime Codex requests.

That working directory must contain a runtime-specific `AGENT.md`.

Required location in the source repository for its template:

```text
backend/app/codex_runtime/workspace_template/AGENT.md
```

For every Codex calendar job:

1. Create a private temporary workspace.
2. Copy the runtime `AGENT.md` into it.
3. Add only relevant calendar context.
4. Start Codex with that workspace as its working directory.
5. Use read-only sandbox access whenever possible.
6. Permit writes only inside that temporary workspace when structured output requires it.
7. Delete or expire the workspace according to a documented retention rule.

The runtime `AGENT.md` must implement the policy defined in `instructions.md`.

---

# 10. Codex Is Not the Security Boundary

Instructions can guide Codex, but backend code must enforce every safety rule.

Codex must never directly update the database.

Codex returns a proposed action.

The backend:

1. Parses the response.
2. Validates the response.
3. Checks calendar permissions.
4. Shows the proposal to the owner.
5. Waits for confirmation.
6. Executes the confirmed action using the calendar service.

Never execute raw commands produced by Codex.

Never treat Codex output as trusted.

---

# 11. Calendar Change Confirmation

All Codex-generated mutations require confirmation.

This includes:

- Creating a calendar
- Renaming a calendar
- Changing a calendar color
- Creating an event
- Updating an event
- Moving an event
- Resizing an event
- Deleting an event
- Editing a recurring event

The assistant may answer read-only questions without confirmation.

The assistant must clearly distinguish:

```text
Suggestion
Awaiting confirmation
Confirmed
Executing
Completed
Failed
```

Codex must never claim that an event was changed until the backend reports successful execution.

---

# 12. Destructive-Action Safety

The runtime assistant must not have a delete-calendar action.

Calendar deletion is manual-owner functionality only.

During the current phase:

- Codex may propose deleting individual events.
- Codex may not propose deleting all events.
- Codex may not perform bulk deletion.
- Codex may not affect more than 10 events in one proposal.
- Codex must ask a clarifying question when a destructive request is ambiguous.
- Recurring-series changes must state whether one occurrence or the full series is affected.

A typo or unclear request must never result in broad deletion.

---

# 13. Documents and LaTeX Safety

M21's Documents foundation is implemented. M22-M24 plan its editor, compiler,
and advice after the M21A-M21I refactoring sequence. Planning does not activate
those milestones; claim new behavior only after implementation and testing.

Document source files and generated PDFs are private owner data. Store source
under a configurable host-backed document root, keep it out of Git, include it
in coordinated backup/restore and relocation checks, and never expose physical
server paths to the browser.

Teacher Assistant must use an established LaTeX distribution and build driver,
not implement its own TeX/LaTeX engine. Compilation must not run inside the
FastAPI process or against the live source directory. Use a disposable source
snapshot and an isolated compiler worker with no network, repository, database,
Docker socket, credentials, other private modules, or arbitrary command access.
Disable shell escape and project-controlled compiler configuration, enforce
resource and owner-configured time limits, and publish only a backend-validated
PDF.

Codex compilation-error advice is read-only. The backend selects bounded,
sanitized log/source context and validates the response. Codex may not edit or
save LaTeX, execute the compiler, install packages, delete projects, or claim a
fix or compilation succeeded.

---

# 14. Testing

Choose what to run according to `guidelines/scope.md`: test the behavior that
was changed and the consumers it affects, and broaden only when a change
crosses a shared contract or integration boundary. Each milestone's
verification section names its required checks.

Add tests for every safety-sensitive rule.

Required test areas:

- Creating calendars
- Updating calendars
- Creating events
- Updating events
- Deleting events
- Read-only calendar enforcement
- Recurring-event behavior
- Assistant proposal validation
- Rejection of unknown Codex actions
- Rejection of invalid calendar IDs
- Rejection of changes to read-only calendars
- Idempotent proposal confirmation

Mock Codex during ordinary tests.

The standard test suite must not require real Codex credentials.

---

# 15. Git Rules

Do not automatically:

- Commit
- Push
- Merge
- Rebase
- Delete branches
- Force-push

Only perform these actions when explicitly requested.

Never delete uncommitted owner work.

Never commit:

- `.env`
- Credentials
- Database data
- Runtime Codex workspaces
- Imported calendar files containing private data
- Logs containing private calendar events
- Private LaTeX projects, generated document PDFs, or compiler logs

---

# 16. Definition of Done

A requested milestone is complete only when:

- Every completion criterion in its milestone file has been verified.
- The milestone's verification passes.
- Docker development still starts.
- Read-only rules are enforced server-side.
- Errors and empty states are handled.
- The existing visual design is preserved.
- No unrelated future module was implemented.
- The checkboxes in the milestone file and `PLAN.md` are accurate and match.
- `handoff.md` and the session report identify the exact next step.
