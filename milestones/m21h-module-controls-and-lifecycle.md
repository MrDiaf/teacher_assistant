# M21H - Module controls and data-preserving lifecycle

- [ ] This milestone

## Outcome

Let the owner enable or disable the five bundled feature modules in Settings
without losing their data, weakening their protections, or managing Docker
through the browser. This is the only new owner-facing capability in the
refactoring sequence; it does not add a new product module.

Dependency: [M21G](m21g-inbox-and-settings-boundary.md). Planning only. All
existing modules remain enabled on upgrade until the owner changes a setting.

## Configuration and dependency behavior

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

## Runtime and data safety

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

## Ordered checklist

- [ ] Persist and validate module state and declared capability dependencies.
- [ ] Add accessible Settings toggles, impact details, and truthful transition states.
- [ ] Enforce route/service/job admission and capability execution checks.
- [ ] Implement bounded lifecycle transitions and restart recovery.
- [ ] Verify preserved data/drafts, coordinated recovery, and re-enable behavior.
- [ ] Test races/stale clients and update platform/module docs, migrations, and status.

## Acceptance criteria

- All-enabled upgrade preserves the current application; each feature can be
  disabled/re-enabled independently with documented optional capability effects.
- Direct routes, integrations, stale proposals, and background jobs cannot use
  a disabled feature; failures remain safe and readable.
- Disabling Inbox stops polling without deleting imported mail or credentials;
  disabling Calendar stops subscriptions without deleting events.
- AI jobs, pending confirmations, active saves/imports, and concurrent toggles
  resolve consistently; repeated enable never starts duplicate workers.
- IDs, hashes, settings, and retained drafts survive disable/re-enable and
  coordinated backup/clean restore, with renewable credentials still excluded.
- Focused/lifecycle/contract tests, real combination E2E, accessibility,
  lint/build, Docker upgrade/startup, recovery, and diff checks pass.

## Expected implementation areas

Platform configuration/migration/API, module catalog/capability registry,
Settings host, lifecycle coordinators, route/service guards, navigation state,
synthetic concurrency/recovery tests, and local documentation.

Stop after verification. [M21I](m21i-modular-verification-and-cutover.md) requires
explicit selection.
