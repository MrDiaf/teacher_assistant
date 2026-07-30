# Teacher Assistant

Teacher Assistant is a single-owner, self-hosted workspace with a personal
calendar, manual course organization, and a private Codex-powered assistant.
Calendar and course features work without Codex. The Assistant can answer
calendar questions and propose calendar changes, but every mutation is
revalidated by the backend and waits for owner confirmation.

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

The Assistant and note summaries share the server-configured model list.
`CODEX_MODEL` is the default, while `AI_ALLOWED_MODELS` is a comma-separated
allowlist. The browser can select only IDs returned by the backend and remembers
the last valid choice locally. Restart the backend after changing either value.

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

## Manual courses

Open **Courses** to create a course with a name, optional course code, term,
description, and color. Courses can be edited, archived, restored, and
permanently deleted after an explicit confirmation.

Each course has a **Materials** tab with separate Literature and Slides
libraries. PDF, PowerPoint (`.pptx`), UTF-8 text, and Markdown files are
text-extracted when uploaded. A failed extraction can be retried, while an
unsupported format is still stored safely.

The **Notes** tab stores private plain text or Markdown notes. A note works
without slides, or it can link to one or more whole slide decks or numbered
slide ranges. Note text is displayed as text and user-entered HTML is never
rendered. AI summaries use only the note body and explicitly linked extracted
slide text. Every stored bullet is labeled **From note**, **From slides**, or
**From note + slides** with its exact source references. Summaries retain the
selected model and source hashes, and are marked stale after their note or
linked slide text changes. Course-linked calendars are not enabled yet.

Deleting one source removes only that source file, its metadata, and its
extracted text. Deleting a slide source also removes references to that source,
but preserves the notes themselves. Deleting a note never deletes a slide file.
Deleting a course removes all its notes, references, literature, and slides.
None of these actions deletes calendars or calendar events. Duplicate course
names are supported because course records are identified by their private IDs.

## Course file storage

The Compose setup stores private course files on the host at:

```text
./data/course_content
```

That directory is bind-mounted into the backend at the path configured by
`COURSE_STORAGE_ROOT` (`/data/course_content` by default). `COURSE_MAX_UPLOAD_MB`
sets the per-file upload limit and defaults to `25`. Both values can be changed
in `.env`; Compose mounts the host directory at the configured container path.

Files use immutable database IDs instead of user-supplied paths:

```text
data/course_content/
└── <course-id>/
    ├── literature/
    │   └── <source-id>/
    │       └── original.<extension>
    └── slides/
        └── <source-id>/
            └── original.<extension>
```

PostgreSQL stores course/source metadata, extraction state, extracted text, page
or slide numbers, content hashes, notes, and slide-reference ranges. The
original binary or text file is stored only under `data/course_content`. Server
paths are not returned to the browser. `data/` is ignored by Git and must remain
private.

Use the Materials tab to remove a source safely. It deletes only the selected
`<source-id>` directory and its database rows, even if the raw file is already
missing. Use the course deletion dialog to remove an entire course directory.
Do not manually delete the storage root while the application is running. If
manual cleanup is necessary, stop the application, make both backups described
below, and remove only the exact course or source ID directory. The stale source
record can then be removed through the Materials tab.

## Backup

Run:

```bash
make backup
```

This writes `backups/teacher-assistant.dump` with permissions restricted to the
current host user. The backup contains private courses, calendars, events,
assistant conversations, proposal history, and subscription URLs. `backups/`
is ignored by Git. Copy the dump only to encrypted, access-controlled storage.

Course source files are stored outside PostgreSQL and require a separate backup.
For a consistent pair of backups, briefly stop writes, create both archives,
and restart:

```bash
docker compose -f compose.yml -f compose.dev.yml stop backend frontend
make backup
tar -C data -czf backups/teacher-assistant-course-content.tar.gz course_content
chmod 600 backups/teacher-assistant-course-content.tar.gz
make dev
```

Keep the database dump and course-content archive together. The archive contains
private course literature and slides. To restore course files, stop the
application and extract the archive under `data/` before running `make dev`.

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

Verify Courses, Calendar, and Assistant history after restore, then sign in to
ChatGPT again if the restored installation does not already have its own
private auth volume. If the database contains course sources, also restore the
matching `teacher-assistant-course-content.tar.gz`; otherwise those source
records will report missing raw files and extraction retries will fail safely.

## Privacy-safe logging

HTTP access logging is disabled because event searches and device-login paths
can contain private values. Application failures log opaque record IDs and error
types, not calendar content, ICS URLs, model output, credentials, or request
bodies. Keep Docker logs private and review them before sharing.

Runtime Codex workspaces are private temporary directories containing only the
relevant bounded calendar context, or one note body plus its explicitly linked
slide text. Tools, network access, repository access, and host filesystem access
are disabled; each workspace is deleted immediately after the job.
