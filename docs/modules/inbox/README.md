# Inbox module

## Ownership and current locations

Inbox owns mail connection metadata, renewable credential storage, verified
TLS/read-only IMAP client, MIME parsing/sync, cursor/scheduler, local messages,
attachments/quarantine/cleanup, mailbox Settings content, UI/styles, and tests.
Current backend code is split across `backend/app/inbox/` and
`backend/app/integrations/`; frontend code is in `features/inbox/`, while its
settings form currently lives in Platform's `features/settings/`. Mail tables
come from migration 0020. Attachments and credentials use separate private
roots; credentials are excluded from backup.

## Required public contracts

- A module entry contributes Inbox routes/page, one mailbox Settings panel,
  scheduler lifecycle, and recovery metadata.
- The Settings contribution exposes rendered UI/actions, never the stored app
  password. Platform hosts it but contains no mail business logic.
- The recovery contribution identifies bounded metadata/attachment content to
  the Platform coordinator without revealing physical paths to other features.

No other feature consumes Inbox data. Inbox owns TLS/read-only enforcement,
bounded parsing, remote immutability, cursor/deduplication, and safe mail errors.
Connection/sync/message services own transactions. Credential replacement and
attachment create/delete retain filesystem compensation and recoverable cleanup.

## Dependencies and migration debt

Inbox depends only on Platform. `inbox` and `integrations` imports in both
directions are internal to this one owner, not a cross-module cycle. Imports of
Calendar's generic enum helper are M21B debt. Platform `main.py` imports routes,
storage, credentials, and scheduler internals until M21B. Settings imports Inbox
API/types directly until M21G. CSS and shared fixtures move in M21G.

## Current commands

```bash
make dev
make check-boundaries
docker compose -p teacher-assistant-test -f compose.yml -f compose.test.yml run --build --rm backend pytest -q tests/test_mail_inbox.py
docker compose -f compose.yml -f compose.dev.yml run --build --rm --no-deps frontend npm run test -- src/features/inbox src/features/settings
make test
make e2e
make data-relocation-test
```

The backend/provider tests use local fakes and no owner credential. These are
not yet isolated module-host commands. See the [M21A baseline](../baseline.md).
