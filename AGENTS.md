# AGENTS.md

## Session Canary

After reading this file at the beginning of a new development session, begin the first response with:

`Ok Overseer`

This confirms that the repository instructions were loaded.

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

# 3. Read Before Working

Before making changes:

1. Read this file.
2. Read `instructions.md`.
3. Read `handoff.md`.
4. Find the selected milestone in the status index in `instructions.md`.
5. Read that milestone file under `milestones/` completely.
6. Inspect the existing implementation and tests.
7. Preserve completed functionality.
8. State which milestone or subtask you will implement.

When M21A creates the module documentation index, follow its ownership map:
read the selected module's README/handoff and the public contracts of relevant
dependencies. Do not read or duplicate every module's history for local work.

If no milestone is active, do not infer one from old specifications, known
limitations, or future-looking notes. Wait for the owner to define or select
the next milestone.

Do not assume something is missing without inspecting the repository.

Do not redesign working pages merely because another design is possible.

---

# 4. One Milestone at a Time

The project must be developed in small, reviewable milestones.

When the owner asks for a milestone:

- Implement only that milestone.
- Do not automatically begin the next milestone.
- Do not scaffold unrelated future features.
- Do not add placeholder backends for future modules.
- Do not mark work complete unless it was tested.
- Stop after the requested milestone and report the result.

When the owner says only `continue`, implement the first incomplete subtask in
the active milestone. If there is no active milestone, ask the owner to define
or select one rather than inventing new scope.

At the end of every development session, report:

```text
Completed:
Tests run:
Known limitations:
Files changed:
Current milestone status:
Recommended next prompt:
```

Update the checklist in the selected milestone file and the status index in
`instructions.md` only after verifying that the acceptance criteria are
satisfied. Update `handoff.md` with the resulting current state and exact next
step.

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

Development must remain Docker-first.

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

- Its acceptance criteria are satisfied.
- Relevant tests pass.
- Docker development still starts.
- Read-only rules are enforced server-side.
- Errors and empty states are handled.
- The existing visual design is preserved.
- No unrelated future module was implemented.
- The milestone checklist is updated accurately.
- The session report identifies the exact next step.
