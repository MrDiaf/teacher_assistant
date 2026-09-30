# Module ownership and dependency index

This is the ownership map for the current modular-monolith transition. M21A
established the baseline and M21B implemented typed metadata, page/router
assembly, bounded backend lifecycle registration, shared UI/platform entry
points, and their enforcement tests. M21C is complete: Documents owns its
internal errors, scoped feature stylesheet, recovery declaration, focused
fixtures/scenarios, and dependency-closed shared host with isolated Docker
commands. M21D is also complete: Calendar owns its public service ports,
errors, styles, scoped tests, and focused host. Courses and Assistant no longer
reach Calendar internals. M21E-M21G remove the remaining
ownership debt and exact legacy exceptions in
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

`make check-module-contract` validates the mirrored frontend/backend metadata
catalogs against each other and this ownership graph. The typed parsers validate
capability requirements and contribution uniqueness without resolving catalog
values to code. Application assembly binds validated metadata to explicit
public code entries. The canonical extension procedure and distinction between
module-safe façades and root-only assembly surfaces are in the
[Platform README](platform/README.md#implemented-composition-extension-points).

Current exact exception count: 22 backend and 3 frontend imports. Removal is
owned by M21E, M21F, and M21G. The manifest
is authoritative down to importer and imported module; this summary is not an
allowlist. Platform composition may import only the exact public module entries
listed in the manifest.

## Repository and data ownership

| Area | Owner | Current locations/data |
| --- | --- | --- |
| React/FastAPI assembly and shell | Platform | `frontend/src/{App,ModuleHost,main}.tsx`, `frontend/src/platform/`, `components/`, `hooks/`, `persistence/`, `backend/app/{main,module_host,platform}/` |
| Shared UI/CSS | Platform host with feature debt | `frontend/src/platform/ui.ts`, `frontend/src/platform/styles.css`; Documents and Calendar styles are scoped under their features, while remaining feature selector families stay in `frontend/src/styles.css` until M21E-M21G |
| Configuration/errors/database | Platform | `backend/app/core/`, `database/`; PostgreSQL session creation is infrastructure, not a public business query API |
| AI/runtime/diagnostics | Platform | `backend/app/{ai,codex_runtime,diagnostics}/`, `frontend/src/features/ai/`; internal paths become public Platform contracts in M21B/M21F |
| Migrations/recovery | Platform coordination | `backend/alembic/`, `backend/app/maintenance/`, `scripts/`, Compose volumes and host bind roots |
| Calendar implementation/data | Calendar | `backend/app/calendar/`, `frontend/src/features/calendar/`; `calendars`, `events` |
| Courses implementation/data | Courses | `backend/app/{courses,course_sources,course_calendars,notes}/`, `frontend/src/features/courses/`; Courses tables and private course-content root |
| Assistant implementation/data | Assistant | `backend/app/assistant/`, `frontend/src/features/assistant/`; Assistant conversation/job/proposal/audit tables |
| Mail implementation/data | Inbox | `backend/app/{inbox,integrations}/`, `frontend/src/features/inbox/`; mail tables, attachment root, credential root |
| Mailbox settings UI | Inbox content, Platform host | currently `frontend/src/features/settings/SettingsPage.tsx`; becomes a registered Inbox contribution in M21G |
| Documents implementation/data | Documents | `backend/app/documents/` including owned errors, `frontend/src/features/documents/` including `styles.css`; document tables and private document root |
| Backend tests | Same feature owner; Platform fixture debt outside Documents/Calendar | `backend/tests/test_*.py`; Documents and Calendar use owned subtrees with scoped fixtures while the root `conftest.py` still resets all owners for other tests |
| Frontend tests | Same feature owner; Platform composition debt | colocated `*.test.*`, plus full-App persistence/Assistant tests |
| Browser tests | Provider/consumer evidence | Documents and Calendar own `e2e/tests/documents.spec.ts` and `e2e/tests/calendar.spec.ts`; remaining combined scenarios stay in `calendar-assistant.spec.ts` until M21E-M21G |

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

Courses and Assistant now use Calendar's typed public contracts. The retained
course-calendar foreign key is an integrity reference, not permission for
Courses to query Calendar tables.

## Transactions and filesystem coordination

Repositories currently flush; application services normally own commits.
Manual single-owner operations remain under their owner. Three boundaries must
be preserved during refactoring:

- Assistant proposal confirmation binds Calendar's restricted command port to
  its application transaction. Calendar commands flush with `commit=False`,
  then the coordinator commits proposal/action/job and Calendar changes once.
  The public port exposes neither the session nor repositories; M21F may move
  the coordinator without changing this atomicity.
- Courses owns course-calendar association changes. Existence/permission checks
  come from Calendar's public query contract; the coordinator commits the link
  change atomically without granting Courses a Calendar repository.
- Course files, Inbox attachments/credentials, and Document sources use
  quarantine/restore/purge or create/rollback compensation around PostgreSQL.
  Platform recovery coordinates all roots and database state; feature public
  contracts never expose their physical paths.

## Known non-import coupling

- `frontend/src/platform/styles.css` now owns root tokens, reset,
  shell/navigation, accessibility, responsive shell, and placeholder rules;
  `frontend/src/styles.css` still mixes the remaining shared-control and feature
  selectors. Platform owns shared button/form/dialog/error rules. Documents now
  owns `.documents-*`, `.document-*`, and its delete-dialog variants.
  Calendar now owns `.calendar-*`, `.month-*`, `.time-*`, `.event-*`, and
  `.ics-*` in `features/calendar/styles.css`;
  `.course-*`, `.courses-*`, note/editor/summary/source
  families in M21E; `.assistant-*`, conversation/proposal/job/composer families
  in M21F; and `.inbox-*`, `.mail-*`, `.connection-*` plus mailbox Settings in
  M21G. Cross-feature selectors such as `.course-calendar .calendar-*` and the
  current `.assistant-error-action` inside Courses require explicit contract or
  shared-primitive decisions in their owning milestones. Preserve cascade and
  design while extracting them.
- Public backend module entries own their existing private-root, scheduler,
  Assistant-registry, and Codex-auth lifecycle bindings. Platform starts only
  supplied entries, unwinds successful starts after startup failure, and bounds
  every shutdown hook. The shared Platform application factory receives an
  explicit entry set: `backend/app/main.py` supplies the complete registered set,
  while focused hosts supply Platform plus either Documents or Calendar.
- `backend/tests/conftest.py` still knows all tables and private roots for the
  assembled suite. Documents and Calendar own closer fixtures; Calendar
  truncates only events/calendars and mounts the real focused host. Focused
  unit commands use isolated PostgreSQL and no owner storage.
- Recovery scripts retain Platform's coordinated quiescence, PostgreSQL dump,
  manifest verification, restore order, and rollback behavior. Documents now
  supplies its established manifest/archive/root identities and safety limits
  through a typed contribution; the other storage components remain named
  directly in `data_archive.py` until their owning milestones.

## Verification baseline

The reproducible cold/warm, full-suite, Documents-focused, startup, lint/build,
E2E, and recovery measurements are in [M21A baseline](baseline.md). They use
synthetic test data and retain known failures rather than changing assertions.
