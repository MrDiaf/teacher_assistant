# M7 — Final calendar hardening

> **LEGACY — ARCHIVED MILESTONE. NOT INSTRUCTIONS.** This milestone was completed
> under the project's retired workflow and is kept as history only. Do not
> follow it, do not treat its checklist as open work, and do not copy its format.
> Current status is in [`PLAN.md`](../../PLAN.md); the current working method is
> in [`guidelines/`](../../guidelines/).

- [x] This milestone

## Outcome

Harden the Calendar and Assistant modules for daily single-owner use through
responsive design, accessibility, auditability, recovery, end-to-end coverage,
and owner documentation.

## Dependencies and boundaries

- Preserve all behavior and safety guarantees from M1–M6.
- Do not expand into Courses, Study Plan, multi-user features, Google OAuth, or
  autonomous Assistant changes.
- Audit records store owner messages, final validated answers, proposals,
  confirmation state, execution result, and safe errors—not hidden reasoning or
  secrets.
- Undo, where practical, applies to recent eligible local changes and may not
  bypass read-only protections.

## Completed checklist

- [x] Improve mobile and narrow-screen layout.
- [x] Review keyboard and screen-reader accessibility.
- [x] Add Assistant audit history.
- [x] Add undo for eligible recent local changes where practical.
- [x] Add end-to-end Calendar/Assistant tests.
- [x] Document Docker setup and normal commands.
- [x] Document Codex authentication.
- [x] Document backup and restore.
- [x] Review logs for private calendar data and secrets.
- [x] Verify existing read-only, proposal, and idempotency rules.

## Acceptance criteria

- Calendar and Assistant are stable enough for daily owner use.
- Core flows are responsive, accessible, and covered end to end.
- Backup/restore and Codex authentication are understandable from `README.md`.
- Safe failures never create partial or unconfirmed changes.
- Logging and audit history do not expose credentials or hidden model reasoning.

## Completion evidence and implementation areas

- Documentation: `README.md`
- End-to-end tests: `e2e/tests/calendar-assistant.spec.ts`
- Backend and frontend Calendar/Assistant test suites
- Application shell and feature styles in `frontend/src/styles.css`

This milestone completed the original Calendar-first product phase. New product
scope required a separately defined phase beginning with M8.
