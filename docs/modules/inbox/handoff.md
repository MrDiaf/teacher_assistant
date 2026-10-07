# Inbox handoff

Current state: M21G is complete. Mail metadata, credentials, IMAP adapters,
parsing/synchronization, local messages, attachments, cleanup, scheduler,
errors, recovery declaration, UI, Settings contribution, styles, and tests are
all owned under the Inbox module. The old top-level `app.integrations` package
and direct Settings-to-Inbox imports are gone.

The full and focused hosts use the same real Inbox public entries. The focused
UI contains Inbox plus the shared Settings page so the owner can exercise the
Inbox-contributed mailbox panel. Platform validates and renders the panel but
contains no mailbox behavior. Dashboard and Study Plan remain unchanged shell
placeholders.

Credential privacy and remote immutability remain enforced: submitted secrets
are stored separately with private permissions, omitted from API responses,
diagnostics, Codex context, and backups, and local read/archive/delete never
issues a remote mutating operation. Missing credentials, TLS/auth failures,
malformed or oversized mail, UIDVALIDITY resets, scheduler/manual races, and
attachment cleanup failures have focused recovery coverage.

Verification on 2026-10-01: `make test-module MODULE=inbox` passed 64 backend,
47 frontend, and one browser/accessibility scenario in about 38 seconds. `make
test` passed 254 backend and 122 frontend tests plus architecture, contract, and
data-safety gates. `make e2e` passed all 19 scenarios; lint, full and focused
production builds, coordinated relocation/restore, live focused Docker health,
and diff hygiene passed. No real mailbox provider was contacted.

Next Inbox work: none is active. M21H may add data-preserving module controls
after explicit owner selection; it must retain the current credential,
read-only, lifecycle, and recovery guarantees.
