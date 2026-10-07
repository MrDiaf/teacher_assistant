# Module ownership and dependency index

This is the ownership map for the current modular-monolith transition. M21A
established the baseline and M21B implemented typed metadata, page/router
assembly, bounded backend lifecycle registration, shared UI/platform entry
points, and their enforcement tests. M21C is complete: Documents owns its
internal errors, scoped feature stylesheet, recovery declaration, focused
fixtures/scenarios, and dependency-closed shared host with isolated Docker
commands. M21D is also complete: Calendar owns its public service ports,
errors, styles, scoped tests, and focused host. Courses and Assistant no longer
reach Calendar internals. M21E is complete as well: Courses owns its public
context contract, errors, styles, recovery declaration, scoped tests, and
focused host, and Assistant no longer reaches Courses internals. M21F is
complete: Assistant owns its feature boundary and consumes Platform's shared
AI/diagnostic contracts. M21G is complete: Inbox owns mail integrations,
Settings contribution, recovery declaration, styles, and focused tests, and it
removed the remaining exact legacy exceptions from
[`architecture/module-boundaries.json`](../../architecture/module-boundaries.json).

## Reading workflow

After the project-wide `AGENTS.md`, `guidelines/`, `instructions.md`, `PLAN.md`,
and root `handoff.md`, read the selected milestone under `guidelines/milestones/`
and the README/handoff for the owner being changed.
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

Current exact exception count: 0 backend and 0 frontend imports. The manifest
is authoritative down to importer and imported module; this summary is not an
allowlist. Platform composition may import only the exact public module entries
listed in the manifest.

## Repository and data ownership

| Area | Owner | Current locations/data |
| --- | --- | --- |
| React/FastAPI assembly and shell | Platform | `frontend/src/{App,ModuleHost,main}.tsx`, `frontend/src/platform/`, `components/`, `hooks/`, `persistence/`, `backend/app/{main,module_host,platform}/` |
| Shared UI/CSS | Platform host and feature-owned styles | `frontend/src/platform/ui.ts`, `frontend/src/platform/styles.css`; Documents, Calendar, Courses, Assistant, and Inbox styles are scoped under their features |
| Configuration/errors/database | Platform | `backend/app/core/`, `database/`; PostgreSQL session creation is infrastructure, not a public business query API |
| AI/runtime/diagnostics | Platform | `backend/app/{ai,codex_runtime,diagnostics}/`, `frontend/src/features/ai/`; public Platform contracts serve Assistant, Courses, and Settings independently |
| Migrations/recovery | Platform coordination | `backend/alembic/`, `backend/app/maintenance/`, `scripts/`, Compose volumes and host bind roots |
| Calendar implementation/data | Calendar | `backend/app/calendar/`, `frontend/src/features/calendar/`; `calendars`, `events` |
| Courses implementation/data | Courses | `backend/app/{courses,course_sources,course_calendars,notes}/`, `frontend/src/features/courses/`; Courses tables and private course-content root |
| Assistant implementation/data | Assistant | `backend/app/assistant/`, `frontend/src/features/assistant/`; Assistant conversation/job/proposal/audit tables |
| Mail implementation/data | Inbox | `backend/app/inbox/` including internal `integrations/`, `frontend/src/features/inbox/`; mail tables, attachment root, credential root |
| Mailbox settings UI | Inbox content, Platform host | Inbox-owned `MailInboxSettingsPanel` registered through `features/inbox/entry.ts`; generic host in `features/settings/` |
| Documents implementation/data | Documents | `backend/app/documents/` including owned errors, `frontend/src/features/documents/` including `styles.css`; document tables and private document root |
| Backend tests | Same feature owner; remaining Platform fixture debt | `backend/tests/test_*.py`; Documents, Calendar, Courses, Assistant, and Inbox use owned subtrees with scoped fixtures while the root `conftest.py` still resets all owners for other tests |
| Frontend tests | Same feature owner; Platform composition debt | colocated `*.test.*`, plus full-App persistence/Assistant tests |
| Browser tests | Provider/consumer evidence | Documents, Calendar, Courses, Assistant, and Inbox own focused specs; cross-module regression scenarios remain in `calendar-assistant.spec.ts` |

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

Courses and Assistant now use Calendar's typed public contracts, and Assistant
uses Courses' typed public context contract. The retained course-calendar
foreign key is an integrity reference, not permission for Courses to query
Calendar tables.

## Transactions and filesystem coordination

Repositories currently flush; application services normally own commits.
Manual single-owner operations remain under their owner. Three boundaries must
be preserved during refactoring:

- Assistant proposal confirmation binds Calendar's restricted command port to
  its application transaction. Calendar commands flush with `commit=False`,
  then the coordinator commits proposal/action/job and Calendar changes once.
  The public port exposes neither the session nor repositories; M21F preserved
  this atomicity while separating diagnostic recording into its own transaction.
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
  `.ics-*` in `features/calendar/styles.css`. Courses now owns `.course-*`,
  `.courses-*`, and its note/editor/summary/source/PDF-viewer families in
  `features/courses/styles.css`. Assistant owns its conversation, proposal,
  job, and composer families; Platform owns shared AI/diagnostic selectors.
  Inbox now owns `.inbox-*`, `.mail-*`, `.connection-*`, and its mailbox
  Settings selectors. The cross-feature
  `.course-calendar .calendar-*` selectors are now an explicit contract:
  Calendar publishes `calendarEmbeddingClasses` and a contract test holds
  Courses to it. The diagnostic action used by Courses is now a Platform-owned
  shared component.
- Feature stylesheets load before the Platform and global sheets, so a feature
  rule cannot out-rank a shared rule of equal specificity by source order.
  Courses names both classes where it refines a shared primitive on the same
  element. Assistant now owns its selectors and Platform owns shared AI and
  diagnostic selectors. The same tie exists, unresolved, for four Calendar elements and one
  Documents element extracted earlier (for example `.create-event-button`
  against `.primary-button`); M21I owns restoring their original appearance.
- `event-dialog` and `event-form` are defined in Calendar's stylesheet but are
  the dialog shell used by Courses and Documents dialogs too. They work because
  every feature stylesheet is bundled; moving them to the shared Platform
  primitives is M21I work.
- Public backend module entries own their existing private-root, scheduler,
  Assistant-registry, and Codex-auth lifecycle bindings. Platform starts only
  supplied entries, unwinds successful starts after startup failure, and bounds
  every shutdown hook. The shared Platform application factory receives an
  explicit entry set: `backend/app/main.py` supplies the complete registered set,
  while focused hosts supply the dependency closure of Documents, Calendar,
  Courses, Assistant, or Inbox. The Inbox host also includes Platform Settings
  so its contributed panel can be exercised.
- `backend/tests/conftest.py` still knows all tables and private roots for the
  assembled suite. Documents, Calendar, Courses, Assistant, and Inbox own closer fixtures;
  Calendar truncates only events/calendars, Courses truncates only Courses and
  Calendar tables with a private per-test course root, and each mounts its real
  focused host. Focused
  unit commands use isolated PostgreSQL and no owner storage. Inbox additionally
  uses isolated test credential and attachment roots.
- Recovery scripts retain Platform's coordinated quiescence, PostgreSQL dump,
  manifest verification, restore order, and rollback behavior. Documents and
  Courses supply their established manifest/archive/root identities and safety
  limits through typed contributions. Inbox supplies the same bounded recovery
  metadata for mail attachments; renewable mail credentials remain excluded.

## Verification baseline

The reproducible cold/warm, full-suite, Documents-focused, startup, lint/build,
E2E, and recovery measurements are in [M21A baseline](baseline.md). They use
synthetic test data and retain known failures rather than changing assertions.
