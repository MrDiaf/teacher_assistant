# M21G - Inbox ownership and contributed Settings panels

## Objective

Make Inbox own its mail workflows end to end, including its Settings panel,
while completing the shell/platform boundary for existing navigation entries.

## Dependencies

Requires M21F to be complete because the shared Settings host must keep the
platform AI contribution introduced there. Inspect the resulting repository
state first; read [M21F](m21f-assistant-and-ai-platform.md) only if additional
intent is required.

This milestone is planned, not active, until the owner selects it.

## Existing-state check

Before making changes:

1. Inspect the relevant repository state.
2. Evaluate every completion criterion below.
3. Mark criteria that are already satisfied, here and in
   [PLAN.md](../../PLAN.md).
4. Run the smallest relevant verification when necessary.
5. If every criterion is already satisfied, mark the milestone complete and
   make no implementation changes.
6. Otherwise, preserve existing correct work and implement only what is missing.

Do not read other milestone files unless they are necessary to resolve
information that cannot be determined from the repository or current
instructions.

## Scope

Authorized areas: Inbox/integrations backend, Inbox and Settings frontend,
module registration, styles, local IMAP/credential/storage tests,
archive/lifecycle contributions, architecture checks, and module documentation.

Not authorized:

- Do not add mail providers, outbound mail, LMS imports, or new Dashboard/Study
  Plan behavior.
- Do not expose a generic plugin/integration framework.

Stop after verification. M21H requires explicit owner selection.

## Required work

Group mail connection metadata, credential storage, IMAP client/parser/sync,
local messages, attachments, cleanup auditing, and scheduler under Inbox
ownership. Retain the internal adapter/service/repository separation. Resolve
existing imports in both directions between integration and Inbox internals
within that owner; do not expose a generic plugin/integration framework.

Move mailbox setup/health UI into an Inbox-owned settings contribution consumed
by the shared Settings host. Keep the platform AI contribution from M21F and
the same routes, secret-submission flow, reconnect/disconnect behavior, and
sanitized errors. Settings hosts panels and owns only common configuration.

Scope Inbox/Settings feature styles, register background lifecycle, and separate
local fake IMAP fixtures and browser tests. Inbox must be exercisable without
Calendar, Courses, Assistant, or Documents runtime activity. A shared credential
utility is permitted only for real existing consumers; mail credentials stay
separate from Codex credentials and remain excluded from coordinated backups.

Use explicit Inbox/platform recovery interfaces for metadata and attachments.
Preserve import deduplication, cursor reset behavior, connection locking,
TLS/read-only enforcement, message/attachment limits, and recoverable cleanup.
The shell continues to own the unchanged Dashboard and Study Plan placeholders.

### Work order

1. Consolidate mail ownership and eliminate unrelated feature imports.
2. Move mailbox Settings implementation into Inbox's registered panel.
3. Scope styles, scheduler hooks, recovery contribution, and local fixtures.
4. Verify the shared host with fake IMAP and real local Inbox API/storage.
5. Audit all migrated modules/platform against M21A ownership; remove the
   remaining scheduled legacy cross-feature boundary exceptions.
6. Update Inbox/platform README/handoffs, wiring guide, timings, and `PLAN.md`.

## Completion criteria

- [ ] Inbox list/detail/search/read/archive/delete, attachments, and every
  mailbox Settings action pass through the same real module entry in full and
  focused apps.
- [ ] Mail credentials never return to the browser after submission or enter
  logs, diagnostics, Codex context, source control, or backup bundles.
- [ ] Missing credentials, TLS/auth errors, malformed mail, UIDVALIDITY changes,
  scheduler/manual races, and attachment cleanup failures remain recoverable.
- [ ] Remote mailbox state is never modified by local read/archive/delete
  actions.
- [ ] Settings contains no Inbox business logic; its registered panels retain
  accessible layout, errors, and behavior. Placeholders remain placeholders.
- [ ] No unscheduled legacy boundary allowance remains for the migrated
  features.
- [ ] Focused/contract tests, Settings/full-app smoke, accessibility,
  lint/build, Docker startup, relevant backup/restore checks, and diff checks
  pass.

## Verification

This milestone changes the shared Settings host and recovery contributions, so
verification covers Inbox, Settings, and the coordinated recovery path.

- Focused Inbox and contract tests using fake IMAP and real local Inbox
  API/storage; no real mailbox credentials.
- `make check-boundaries` with no unscheduled legacy allowance for the migrated
  features.
- Settings and full-application smoke plus accessibility scenarios
  (`make e2e`).
- `make test` as the affected-consumer gate for the shared Settings host.
- `make lint` and the frontend production build.
- Docker startup.
- Relevant backup/restore checks (`make data-relocation-test`).
- `git diff --check`.
