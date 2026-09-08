# Module ownership and dependency index

This is the M21A ownership map for the current modular-monolith transition. It
describes the repository as it exists at revision `dcada0a` plus the M21A
documentation and checks. Feature directories are not yet isolated modules;
M21B-M21G remove the exact legacy exceptions recorded in
[`architecture/module-boundaries.json`](../../architecture/module-boundaries.json).

## Reading workflow

After the project-wide `AGENTS.md`, `instructions.md`, and root `handoff.md`,
read the selected milestone and the README/handoff for the owner being changed.
Read dependency READMEs only for contracts the change consumes. Do not load all
module histories for an ordinary local change.

| Owner | Scope | Documentation |
| --- | --- | --- |
| Platform | application composition, navigation, Settings host, shared UI, configuration, database/migrations, recovery coordination, AI runtime and diagnostics | [README](platform/README.md), [handoff](platform/handoff.md) |
| Calendar | calendars, events, recurrence, ICS import/subscriptions, permission enforcement | [README](calendar/README.md), [handoff](calendar/handoff.md) |
| Courses | courses, sources, notes, summaries/prettify, course-calendar associations | [README](courses/README.md), [handoff](courses/handoff.md) |
| Assistant | conversations, context selection, jobs, proposals, confirmation/cancellation | [README](assistant/README.md), [handoff](assistant/handoff.md) |
| Inbox | mail connection/credentials, IMAP sync, messages, attachments, mailbox Settings contribution | [README](inbox/README.md), [handoff](inbox/handoff.md) |
| Documents | M21 project/tag/source foundation only | [README](documents/README.md), [handoff](documents/handoff.md) |

Dashboard and Study Plan are Platform-owned shell placeholders. They are not
feature modules or services.

## Dependency rules

The intended acyclic business dependency graph is:

```text
Assistant -> Courses -> Calendar -> Platform
Assistant ------------> Calendar
Inbox ------------------------------> Platform
Documents --------------------------> Platform
```

Platform composition may register module public entries, but this assembly is
not permission for Platform business code to reach feature internals. A module
may import its own internals and approved Platform primitives. Cross-feature
access must use a typed public contract declared by the provider. Contracts may
return bounded value objects and explicit errors only—not ORM entities,
repositories, credentials, physical paths, SQL, or an unrestricted session.

`make check-boundaries` parses Python with the standard AST and TypeScript with
the installed TypeScript compiler. It validates the declared graph, rejects any
cross-owner import not in the exact legacy list, rejects stale exceptions, and
proves both checks fail on deliberately invalid fixtures. `make test` runs this
gate before application tests. New wildcard exceptions and new cycles are not
permitted.

Current exact exception count: 63 backend and 21 frontend imports. Removal is
owned by M21B (33), M21D (20), M21E (4), M21F (25), and M21G (2). The manifest
is authoritative down to importer and imported module; this summary is not an
allowlist.

## Repository and data ownership

| Area | Owner | Current locations/data |
| --- | --- | --- |
| React/FastAPI assembly and shell | Platform | `frontend/src/{App,main}.tsx`, `components/`, `hooks/`, `persistence/`, `backend/app/main.py` |
| Shared UI/CSS | Platform host with feature debt | `frontend/src/styles.css`; feature selector families remain globally coupled until M21C-M21G |
| Configuration/errors/database | Platform | `backend/app/core/`, `database/`; PostgreSQL session creation is infrastructure, not a public business query API |
| AI/runtime/diagnostics | Platform | `backend/app/{ai,codex_runtime,diagnostics}/`, `frontend/src/features/ai/`; internal paths become public Platform contracts in M21B/M21F |
| Migrations/recovery | Platform coordination | `backend/alembic/`, `backend/app/maintenance/`, `scripts/`, Compose volumes and host bind roots |
| Calendar implementation/data | Calendar | `backend/app/calendar/`, `frontend/src/features/calendar/`; `calendars`, `events` |
| Courses implementation/data | Courses | `backend/app/{courses,course_sources,course_calendars,notes}/`, `frontend/src/features/courses/`; Courses tables and private course-content root |
| Assistant implementation/data | Assistant | `backend/app/assistant/`, `frontend/src/features/assistant/`; Assistant conversation/job/proposal/audit tables |
| Mail implementation/data | Inbox | `backend/app/{inbox,integrations}/`, `frontend/src/features/inbox/`; mail tables, attachment root, credential root |
| Mailbox settings UI | Inbox content, Platform host | currently `frontend/src/features/settings/SettingsPage.tsx`; becomes a registered Inbox contribution in M21G |
| Documents implementation/data | Documents | `backend/app/documents/`, `frontend/src/features/documents/`; document tables and private document root |
| Backend tests | Same feature owner; Platform fixture debt | `backend/tests/test_*.py`; `conftest.py` truncates every table and clears every storage root |
| Frontend tests | Same feature owner; Platform composition debt | colocated `*.test.*`, plus full-App persistence/Assistant tests |
| Browser tests | Joint provider/consumer evidence | one combined `e2e/tests/calendar-assistant.spec.ts`; split ownership is scheduled in M21C-M21G |

Migrations stay centrally ordered even when their tables have a feature owner:
0001-0005 Calendar, 0006-0009 Assistant, 0010-0014 Courses, 0015-0017
Assistant/Platform diagnostics, 0018 Courses, 0019 Platform compatibility,
0020 Inbox, and 0021 Documents.

## Integrity references versus business access

Database foreign keys remain intact and do not authorize table queries:

- Courses owns `course_calendar_links`; its `calendar_id -> calendars.id`
  foreign key protects integrity while Calendar owns calendar/event behavior.
- Assistant's `assistant_jobs.diagnostic_error_id -> diagnostic_errors.id` is
  an integrity reference to Platform diagnostics. Diagnostic access still needs
  a bounded Platform contract.
- Notes/source/summary foreign keys remain internal to Courses; mail connection,
  message, attachment, and quarantine foreign keys remain internal to Inbox.
- Document project/tag join references remain internal to Documents.

Current direct Calendar ORM/repository queries by Courses and Assistant are
business access violations, not exceptions justified by these foreign keys.

## Transactions and filesystem coordination

Repositories currently flush; application services normally own commits.
Manual single-owner operations remain under their owner. Three boundaries must
be preserved during refactoring:

- Assistant proposal confirmation revalidates and performs all Calendar
  commands with `commit=False`, then commits proposal/action/job and Calendar
  changes once. M21D/M21F must replace this shared-session coupling with an
  explicit application coordinator, not partial commits or a public session.
- Courses owns course-calendar association changes. Existence/permission checks
  come from Calendar's public query contract; the coordinator commits the link
  change atomically without granting Courses a Calendar repository.
- Course files, Inbox attachments/credentials, and Document sources use
  quarantine/restore/purge or create/rollback compensation around PostgreSQL.
  Platform recovery coordinates all roots and database state; feature public
  contracts never expose their physical paths.

## Known non-import coupling

- `frontend/src/styles.css` mixes shell and every feature's selectors. Platform
  owns root tokens, reset, shell/navigation, shared button/form/dialog/error,
  accessibility, responsive, and placeholder rules. `.documents-*` and
  `.document-*` move in M21C; `.calendar-*`, `.month-*`, `.time-*`, `.event-*`,
  and `.ics-*` in M21D; `.course-*`, `.courses-*`, note/editor/summary/source
  families in M21E; `.assistant-*`, conversation/proposal/job/composer families
  in M21F; and `.inbox-*`, `.mail-*`, `.connection-*` plus mailbox Settings in
  M21G. Cross-feature selectors such as `.course-calendar .calendar-*` and the
  current `.assistant-error-action` inside Courses require explicit contract or
  shared-primitive decisions in their owning milestones. Preserve cascade and
  design while extracting them.
- `backend/app/main.py` owns all router, storage-root, scheduler, Assistant
  registry, and Codex shutdown hooks. M21B introduces explicit lifecycle entries.
- `backend/tests/conftest.py` knows all tables and private roots; tests share one
  database reset. M21C-M21G introduce owner fixtures without weakening full tests.
- Recovery scripts and `data_archive.py` know every storage component by name.
  This is intentional Platform coordination, later expressed as typed recovery
  contributions rather than independent backups.

## Verification baseline

The reproducible cold/warm, full-suite, Documents-focused, startup, lint/build,
E2E, and recovery measurements are in [M21A baseline](baseline.md). They use
synthetic test data and retain known failures rather than changing assertions.
