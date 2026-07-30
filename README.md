# Teacher Assistant

Teacher Assistant is a single-owner, self-hosted calendar with a private
Codex-powered assistant. Calendar features work without Codex. The Assistant can
answer questions and propose changes, but every mutation is revalidated by the
backend and waits for owner confirmation.

## Requirements

- Docker with Docker Compose
- Git
- Make
- A modern browser

Python and Node.js are not required on the host.

## Setup

```bash
cp .env.example .env
make dev
```

Before keeping private data in the application, edit `.env` and replace the
development database password. `.env` is ignored by Git.

Open the application at:

- This computer: `http://localhost:5173`
- Trusted local network: `http://ronny-server:5173`

If the server uses another hostname, add it to `server.allowedHosts` in
`frontend/vite.config.ts`. The backend listens on port `8000` and the frontend
on `5173` by default; both can be changed in `.env`.

Keep the application on a trusted local network. This phase is not designed for
public internet exposure and does not include multi-user authentication.

## Daily commands

```bash
make dev       # build and start
make down      # stop
make restart   # restart containers
make logs      # follow application logs
make migrate   # apply database migrations
make test      # isolated backend and frontend tests
make e2e       # isolated Playwright browser tests
make lint      # Python, TypeScript, and formatting checks
make backup    # private PostgreSQL backup
```

Both test commands use separate temporary databases and remove their Docker
volumes after the run. They never truncate the owner database.

## ChatGPT subscription authentication

Open **Assistant** and select **Sign in with ChatGPT**. Teacher Assistant starts
Codex device authentication and shows an OpenAI link plus a one-time code. Open
the link, sign in to the desired ChatGPT workspace, enter the code, then return
to Teacher Assistant. No API key is required for this path.

The renewable Codex session is stored in the private `codex-auth-data` Docker
volume on this installation. It is not sent to the browser and must never be
committed, copied into support tickets, or shared. OpenAI documents that
file-based Codex credentials contain access tokens and should be treated like a
password. See the official [Codex authentication documentation](https://learn.chatgpt.com/docs/auth).

Use **Sign out** in the Assistant sidebar to remove the stored session. Active
ChatGPT sessions normally refresh automatically; if the connection expires,
sign in again from the Assistant page.

An `OPENAI_API_KEY` in `.env` is supported only as an optional usage-billed
fallback. API-key usage is billed through the OpenAI Platform account rather
than a ChatGPT subscription.

## Calendar-change safety

- Read-only calendars remain viewable and searchable but cannot be mutated.
- The backend rechecks IDs, permissions, and stale timestamps at confirmation.
- Codex cannot delete calendars or bulk-delete events.
- A deletion proposal may target only one event.
- One executable proposal may affect at most 10 events and executes in one
  database transaction.
- Requests for 11–100 independent event creations may be shown as one linked
  plan of separately confirmed batches. Confirming one batch never confirms the
  others.
- Confirmation is idempotent.
- Recent manual event edits expose a short-lived **Undo** action where restoring
  the prior state is safe and practical.
- Recurring changes require one occurrence or the complete series. “This and
  following” is not supported.

Assistant proposal lifecycle records are available under **Assistant →
Activity**. They show requested, confirmed, and executed timestamps without
placing calendar contents in application logs.

## Backup

Run:

```bash
make backup
```

This writes `backups/teacher-assistant.dump` with permissions restricted to the
current host user. The backup contains private calendars, events, assistant
conversations, proposal history, and subscription URLs. `backups/` is ignored
by Git. Copy the dump only to encrypted, access-controlled storage.

The ChatGPT credential volume is intentionally not included. Reauthenticate
after restoring to another installation instead of copying renewable access
tokens.

### Restore

Restoring replaces the current database. Make a fresh backup first, then run:

```bash
docker compose -f compose.yml -f compose.dev.yml stop backend frontend
docker compose -f compose.yml -f compose.dev.yml exec -T database \
  sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose -f compose.yml -f compose.dev.yml exec -T database \
  sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' \
  < backups/teacher-assistant.dump
make dev
```

Verify the Calendar and Assistant history after restore, then sign in to ChatGPT
again if the restored installation does not already have its own private auth
volume.

## Privacy-safe logging

HTTP access logging is disabled because event searches and device-login paths
can contain private values. Application failures log opaque record IDs and error
types, not calendar content, ICS URLs, model output, credentials, or request
bodies. Keep Docker logs private and review them before sharing.

Runtime Codex workspaces are private temporary directories containing only the
relevant calendar context. Tools, network access, repository access, and host
filesystem access are disabled; each workspace is deleted immediately after the
job.
