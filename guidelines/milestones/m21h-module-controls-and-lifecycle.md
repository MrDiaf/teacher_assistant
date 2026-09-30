# M21H - Module controls and data-preserving lifecycle

## Objective

Let the owner enable or disable the five bundled feature modules in Settings
without losing their data, weakening their protections, or managing Docker
through the browser. This is the only new owner-facing capability in the
refactoring sequence; it does not add a new product module.

## Dependencies

Requires M21G to be complete because module controls build on the contributed
Settings panels and the fully migrated module boundaries. Inspect the resulting
repository state first; read [M21G](m21g-inbox-and-settings-boundary.md) only if
additional intent is required.

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

Authorized areas: Platform configuration/migration/API, module
catalog/capability registry, Settings host, lifecycle coordinators,
route/service guards, navigation state, synthetic concurrency/recovery tests,
and local documentation.

Not authorized: uninstalling code, deleting module data, runtime plugin
downloads, per-module deployment control, and browser access to the Docker
socket are out of scope.

Stop after verification. M21I requires explicit owner selection.

## Required work

All existing modules remain enabled on upgrade until the owner changes a
setting.

### Configuration and dependency behavior

Store the enabled set as validated, server-authoritative installation settings.
Only code-owned Calendar, Courses, Assistant, Inbox, and Documents IDs are
toggleable. Shell, Settings, recovery, diagnostics, and shared AI infrastructure
remain available. Reject unknown IDs and attempts to disable required platform
services. Do not accept filesystem paths, package URLs, or executable names.

Distinguish required dependencies from optional capabilities. Courses can keep
notes/materials while its Calendar integration is unavailable. Assistant may
answer general questions when Calendar/Courses capabilities are disabled; it
must not include their data or propose/use unavailable actions. Disabling the
Assistant page does not disable Course summaries/prettify or platform sign-in.
Explain affected capabilities before applying a change; reject invalid required
dependency combinations instead of silently cascading module changes.

### Runtime and data safety

Enforce disabled state at backend routes, public service/capability entry points,
and job admission as well as navigation. Direct API calls and old open tabs
must not bypass it. Recheck capability availability at proposal execution.
Read-only calendar rules and confirmations remain independent requirements.

Serialize configuration transitions. Stop admitting new affected work before
settling in-flight jobs through bounded draining or existing safe cancellation.
Do not kill a committed data transaction halfway through; do not report Disabled
until affected activity is settled. On timeout/failure show the actual state
and retain a recoverable consistent configuration. Handle restart, repeated
requests, and concurrent toggle/job requests without duplicate schedulers.

Retain database rows, source files, attachments, and credentials on disable.
Mailbox disconnect remains a separate explicit credential action. Migration,
backup, restore, and recovery of stored data must include disabled modules.
Re-enable restores access without reseeding data or resetting identities.

Navigation falls back to an available page. Warn about unsaved local drafts
before owner-initiated navigation/disable, preserve stored drafts, and handle
stale tabs safely. Disabled UI state is not an excuse to purge owner content.
Uninstalling code, deleting module data, runtime plugin downloads, per-module
deployment control, and browser access to the Docker socket are out of scope.

### Work order

1. Persist and validate module state and declared capability dependencies.
2. Add accessible Settings toggles, impact details, and truthful transition
   states.
3. Enforce route/service/job admission and capability execution checks.
4. Implement bounded lifecycle transitions and restart recovery.
5. Verify preserved data/drafts, coordinated recovery, and re-enable behavior.
6. Test races/stale clients and update platform/module docs, migrations, and
   `PLAN.md`.

## Completion criteria

- [ ] All-enabled upgrade preserves the current application; each feature can be
  disabled/re-enabled independently with documented optional capability effects.
- [ ] Direct routes, integrations, stale proposals, and background jobs cannot
  use a disabled feature; failures remain safe and readable.
- [ ] Disabling Inbox stops polling without deleting imported mail or
  credentials; disabling Calendar stops subscriptions without deleting events.
- [ ] AI jobs, pending confirmations, active saves/imports, and concurrent
  toggles resolve consistently; repeated enable never starts duplicate workers.
- [ ] IDs, hashes, settings, and retained drafts survive disable/re-enable and
  coordinated backup/clean restore, with renewable credentials still excluded.
- [ ] Focused/lifecycle/contract tests, real combination E2E, accessibility,
  lint/build, Docker upgrade/startup, recovery, and diff checks pass.

## Verification

This milestone changes shared configuration, migrations, and every module's
admission path, so verification is application-wide.

- Focused lifecycle and contract tests, including synthetic concurrency, stale
  client, and restart cases.
- Real module-combination browser and accessibility scenarios (`make e2e`).
- `make test`, including the boundary, contract, and data-safety gates.
- `make lint` and the frontend production build.
- Docker upgrade and startup with all modules enabled.
- Coordinated recovery with disabled modules included
  (`make data-relocation-test`).
- `git diff --check`.
