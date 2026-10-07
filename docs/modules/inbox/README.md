# Inbox module

## Ownership and current locations

Inbox owns mail connection metadata, renewable credential storage, the verified
TLS/read-only IMAP adapter, MIME parsing and synchronization, cursor and
scheduler behavior, local messages, attachments, quarantine and cleanup,
mailbox Settings content, UI/styles, recovery metadata, and tests.

Backend implementation is under `backend/app/inbox/`, including the internal
`integrations/` adapter/service/repository layers. Frontend implementation is
under `frontend/src/features/inbox/`. Mail tables come from migration 0020.
Attachments and credentials use separate private roots; credentials are never
returned after submission and are excluded from coordinated backups.

## Public contracts

- `backend/app/inbox/entry.py` contributes Inbox routes, credential and
  attachment root initialization, the mail scheduler, and the bounded recovery
  declaration used by Platform.
- `frontend/src/features/inbox/entry.ts` contributes both the Inbox page and
  `MailInboxSettingsPanel` to the shared Platform host. The same entry is used
  by the full and focused applications.
- The Settings contribution owns setup, health, test, check-now, reconnect, and
  disconnect behavior. Platform only validates, orders, and renders contributed
  panels.
- The recovery declaration publishes stable manifest/archive/root identities,
  format introduction, and safety limits. It exposes no live path, credential,
  repository, session, or executable callback.

No other business feature consumes Inbox data. Inbox owns TLS/read-only
enforcement, bounded parsing, remote immutability, cursor/deduplication, and
safe mail errors. Connection, synchronization, and message services own their
transactions. Credential replacement and attachment create/delete retain
filesystem compensation and recoverable cleanup.

## Dependencies and boundaries

Inbox depends only on Platform. Platform composition imports the exact Inbox
public entries; Platform Settings and recovery coordination contain no Inbox
business logic. The architecture manifest has no Inbox legacy exception and no
feature has access to mail credentials, messages, attachments, or internals.

Inbox styles are loaded by its frontend entry from
`frontend/src/features/inbox/styles.css`. Backend tests live under
`backend/tests/inbox/` with a scoped real-host fixture and isolated credential
and attachment roots. The focused browser stack mounts only its isolated Inbox
private storage.

## Current commands

```bash
make dev
make check-boundaries
make check-module-contract
make dev-module MODULE=inbox
make test-module MODULE=inbox
make logs-module MODULE=inbox
make down-module MODULE=inbox
make test
make e2e
make lint
make data-relocation-test
```

The focused tests use local fake IMAP and real local Inbox API/storage. They do
not use owner credentials or contact a real provider. See the
[M21A baseline](../baseline.md) for the project-wide baseline.
