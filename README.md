# Teacher Assistant

Teacher Assistant is a single-owner, self-hosted workspace with a personal
calendar, manual course organization, a forwarded-mail Inbox, durable private
LaTeX document projects, and a private Codex-powered assistant.
Calendar and course features work without Codex. The Assistant is a general
helper for explanations, writing, planning, study aids, and code snippets; it
can also answer calendar questions, use relevant course notes with validated
citations, explain sanitized application errors, and propose calendar changes.
Every mutation is revalidated by the backend and waits for owner confirmation.

## Development roadmap

M1-M21, M21A, and M21B are implemented. M21C is active; its first two subtasks
give Documents explicit internal error ownership, feature-scoped styling, and a
bounded recovery contribution used by Platform's coordinated archive/restore
flow. Its shared module-host, focused-fixture, boundary, and workflow subtasks
remain incomplete.
M21B-M21I precede the LaTeX editor/compiler/advice work in M22-M24. The
refactoring sequence covers ownership and public contracts, application
composition, a Documents pilot, the other existing modules, Settings module
controls, and focused Docker testing with final recovery verification.

See the [authoritative milestone index](instructions.md#milestone-status), the
[module ownership index](docs/modules/README.md), and the completed composition
milestone [M21B](milestones/m21b-application-composition.md). Module switches,
module-specific Docker commands, and the isolated module host are planned,
not available features yet.

## Application composition wiring

Teacher Assistant uses mirrored, validated module metadata plus statically
imported public code entries; it does not load plugins or executable names from
configuration or browser input. Frontend pages are bound in
`frontend/src/platform/modules/frontendCatalog.ts` and rendered through
`App.tsx`. Backend routers and lifecycle hooks are bound in
`backend/app/platform/modules/backend_catalog.py` and consumed by
`backend/app/main.py`. Existing modules remain enabled by default.

The exact extension procedure, selective-test assembly path, lifecycle cleanup
rules, and approved shared Platform imports are documented in the
[Platform module README](docs/modules/platform/README.md). Adding a product
module or page still requires an explicitly selected milestone.

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

On the first `make dev`, the `teacher-assistant-change-me` placeholder is
replaced in the private `.env` with a unique installation identity. That
identity is also recorded in the ignored `.teacher-assistant-installation`
marker. Keep both hidden files when moving the installation: the stable
identity reconnects PostgreSQL, Codex authentication, and private integration
credentials after a rename.

Do not copy `.env.example` over an existing `.env`. An installation created
before the stable identity was added must run `make data-preflight`, stop with
`make down`, and use the explicit `make data-adopt` procedure in
[Data durability and recovery](docs/data-durability.md). Normal Make targets
refuse to create a replacement database when recorded data appears missing.

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
make check-boundaries # reject new cross-module imports and dependency cycles
make test      # boundaries plus isolated backend and frontend tests
make e2e       # isolated Playwright browser tests
make lint      # Python, TypeScript, and formatting checks
make data-preflight # read-only data-resolution report
make backup    # coordinated PostgreSQL + course/mail/document-file backup
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

## Browser navigation convenience state

This browser profile remembers a small set of owner-controlled navigation
choices under the versioned `teacher-assistant.ui-state.v1` site-storage key:
the active module (including Inbox and Documents); main and per-course Calendar
view/anchor; selected course and
tab; selected Assistant conversation/sidebar; and unsent composer text per
conversation, including a separate not-yet-created conversation draft. The
schema accepts only known values, UUIDs, real `YYYY-MM-DD` dates, bounded text,
and timestamps. It keeps at most 20 drafts of up to 4,000 characters and 50
per-course Calendar preferences.

This convenience state is not an offline cache. Events, courses, notes,
summaries, messages, proposals, permissions, authentication data, errors, and
active operations are never stored there and are always reloaded from FastAPI.
Assistant drafts stay in this browser until sent successfully or cleared with
**Clear draft**; failed or cancelled sends retain the matching draft. Corrupt,
disabled, unavailable, or full browser storage falls back safely to defaults.

Clearing site data, using a private window, or opening another browser profile
or device removes these navigation choices and unsent drafts. It does not
delete any backend record. Note and summary expansion is intentionally not
remembered, so Notes always remounts minimized.

## Forwarded-mail Inbox

Teacher Assistant receives only mail that the owner deliberately forwards to a
separate, dedicated mailbox. First create that mailbox with an IMAP-capable mail
provider, enable an app password when required, and add a forwarding rule in
the school or personal account that receives the original mail. Provider menus
differ; look for **Forwarding**, **Rules**, or **Filters** and forward only the
messages you want copied into Teacher Assistant.

Open **Settings → Mail inbox** and enter the provider's IMAP hostname, port,
TLS mode, mailbox name, dedicated-mailbox username, and app password. The
backend resolves only public targets, requires certificate-verified implicit
TLS or STARTTLS, authenticates, and opens the mailbox read-only. Use **Test
connection** or **Check mail**; otherwise the backend polls at
`MAIL_SYNC_INTERVAL_SECONDS` (five minutes by default) with bounded backoff.

Teacher Assistant does not create an address, configure DNS/MX records or
forwarding, send or reply to mail, manage contacts, or modify the remote
mailbox. It never sets Seen, moves, archives, deletes, or expunges remote mail.
Inbox read/unread, archive, and single-message deletion are local states. Local
deletion requires confirmation and removes only that stored item and its local
attachment files.

Mail is labeled **Mail** and forwarded body content is explicitly unverified;
quoted text is never treated as a verified original sender. Plain text is
preferred. HTML-only bodies are sanitized on ingestion and displayed as
passive text, so scripts, forms, SVG, iframes, tracking pixels, remote images,
and active embeds cannot load. Attachments are bounded, stored under generated
IDs, and offered only as downloads with private/no-store and `nosniff`
headers. Mail never becomes Course material, Calendar data, or Assistant/Codex
context automatically.

The renewable app password is stored only in the private
`integration-credential-data` volume with strict permissions. It is never
returned by the API, written to browser storage, included in diagnostics or
Codex workspaces, or placed in coordinated backups. A missing or corrupt secret
shows **Reconnect required** while already imported mail remains available.

## Private document projects

Open **Documents** to create private LaTeX projects. Project titles may repeat;
an immutable UUID identifies each source directory. The overview supports
case-insensitive title search, composable colored-tag filters, multiple tags per
project, rename, source downloads, and explicitly confirmed deletion. Deleting
a tag removes only its project associations. Tag names are trimmed and unique
under Unicode case-folded comparison, so capitalization variants cannot create
duplicate tags.

Each new project starts with a valid `main.tex` beneath
`DOCUMENT_DATA_DIR` (default `./data/document_projects`). PostgreSQL contains
only metadata and associations; physical host paths are never returned by the
API. `DOCUMENT_MAX_SOURCE_MB` bounds a project's generated source download.
The `.tex` endpoint returns only `main.tex`, while Source ZIP contains only the
validated root-relative source tree—never build files, logs, database metadata,
credentials, or another project.

M21 is an overview and recovery foundation. Multi-file editing, compilation,
PDF preview, and Codex compilation advice are not part of this milestone. Stop
application writes before manually inspecting or copying raw source folders.

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

## Course-aware Assistant

The main Assistant can answer general questions from built-in model knowledge
without requiring calendar or note citations. It can explain concepts,
brainstorm, draft text, create study aids, and return text or code snippets in
chat. It cannot open an interactive editor, control the clipboard, execute
code, browse the web, or inspect the source repository.

It can also answer private note questions such as “Summarize my latest notes
from Datasekretess” or “What did I write about normalization?” The backend
selects a bounded set of matching notes before starting Codex. Private note
matching runs only when the owner explicitly mentions notes or slides, or asks
what they previously wrote. Generic topic overlap, general writing requests,
and capability questions such as “What can you do with course notes?” do not
load private note bodies and do not require a citation. Calendar-only requests
receive every calendar, including hidden and read-only calendars, without note
context; an explicitly named course-calendar question remains limited to that
course's linked calendars. Only notes selected for an actual content-grounded
question, their explicitly linked slide ranges, and calendars linked to the
selected course are supplied. Unrelated courses, literature, source files, and
private calendar data are excluded. If matching notes belong to several
courses, the Assistant asks which course you mean before any runtime job
starts.

Answers grounded in course notes display validated note-title citations and,
where used, the exact slide deck and slide number. General-knowledge,
capability, and calendar-only answers use an empty citation list. An invented
or out-of-scope ID or citation fails the Assistant job safely and does not save
the answer or alter any data. Notes, sources, courses, and slide links remain
read-only to the runtime Assistant.

While a request is running, the chat shows elapsed thinking states and a
**Cancel request** control. Cancellation is handled by the backend: the active
Codex task is interrupted, its temporary workspace is removed, the job is
stored as cancelled, and no answer or calendar proposal is saved. A request
that finishes just before cancellation remains completed rather than being
rewritten as cancelled. Cancelled prompts remain visible in owner history but
are excluded from later model conversation context, so a follow-up does not
accidentally answer work the owner stopped.

If the first model response is malformed or fails the strict response/citation
schema, the backend supplies the safe validation feedback to Codex and makes
one automatic correction attempt. Only when that second response also fails is
the error card shown. Automatic correction never bypasses proposal validation,
read-only calendars, or owner confirmation.

## Manual courses

Open **Courses** to create a course with a name, optional course code, term,
description, and color. Courses can be edited, archived, restored, and
permanently deleted after an explicit confirmation.

Each course has a **Materials** tab with separate Literature and Slides
libraries. PDF, PowerPoint (`.pptx`), UTF-8 text, and Markdown files are
text-extracted when uploaded. A failed extraction can be retried, while an
unsupported format is still stored safely.

Uploaded PDF cards provide **Open PDF** for a large viewer inside Teacher
Assistant and **Open in new window** for the browser's native PDF view. The
viewer keeps the Materials tab in place, supports keyboard closing and focus
return, and offers the new-window fallback when embedding is unavailable. Both
Literature and Slides PDFs use the same private source-ID endpoint; other file
types do not expose a PDF action.

The **Notes** tab stores private plain text or Markdown notes, up to 100,000
characters each. Its lightweight editor keeps Markdown markers visible while
highlighting headings, bold, italic, lists, blockquotes, links, inline code,
and fenced code blocks. The toolbar provides the common formatting operations,
Ctrl/Cmd+B and Ctrl/Cmd+I work on the current selection, and **Plain text**
turns highlighting off without changing the stored source.

**Prettify** sends only the current unsaved note body to the selected model in
a private, temporary Codex workspace. It corrects only clear spelling,
capitalization, punctuation, and grammar issues. The backend rejects output
that changes Markdown structure or protected code, links, URLs, formulas,
citations, and quoted text. Drafts are limited to 40,000 characters for this
operation and are never silently truncated.

The complete original and proposed Markdown are shown before anything changes.
**Keep my version** leaves the draft byte-for-byte unchanged; **Use prettified
version** replaces only the local editor draft and returns focus to the editor.
Neither action saves the note. Use **Create note** or **Save changes** separately
after reviewing and making any further edits. Failure, cancellation, invalid
output, or closing the dialog never writes the suggestion to the database.

Note cards safely render that same supported Markdown subset. Raw HTML remains
readable text, embedded content is never created, and unsafe link schemes such
as `javascript:` and `data:` are not clickable. The original Markdown string
is preserved exactly through save and reopen; no rich-text document format is
introduced.

Every note starts minimized when the Notes tab is opened, reloaded, or revisited.
Its compact header keeps the title, update date, slide-reference count, and
summary state visible. Expanding one note does not open any other note, and its
nested summary has a separate expand control that also starts minimized. These
temporary expansion choices are deliberately not saved between Notes visits.

A note works without slides, or it can link to one or more whole slide decks or
numbered slide ranges. AI summaries use only the original note body and
explicitly linked extracted slide text. Every stored bullet is labeled **From
note**, **From slides**, or **From note + slides** with its exact source
references. Summaries retain the selected model and source hashes, and are
marked stale after their note or linked slide text changes.

Each completed summary bullet has an accessible cross button that removes only
that persisted bullet. Bullet identity is assigned and checked by the backend,
so repeated or concurrent requests cannot shift to a different list item.
Removing the last bullet leaves the source note, slide links, provenance, and
uploaded files unchanged and shows an empty state with **Generate again**.

The **Calendar** tab links a course to existing calendars without copying
events. Unlinking or deleting a course does not delete a calendar or its events,
and read-only calendar protections remain unchanged.

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
`COURSE_STORAGE_ROOT` (`/data/course_content` by default). The host path can be
changed independently with `COURSE_DATA_DIR`; a relative value moves with the
complete project directory. `COURSE_MAX_UPLOAD_MB` sets the per-file upload
limit and defaults to `25`.

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

Private Inbox attachments are stored separately at `MAIL_DATA_DIR` (default
`./data/mail_attachments`) and mounted at `MAIL_STORAGE_ROOT`. Paths are built
only from database UUIDs; sender filenames are display/download metadata, not
filesystem paths. `MAIL_MAX_MESSAGE_MB`, `MAIL_MAX_ATTACHMENT_MB`, and
`MAIL_MAX_TOTAL_STORAGE_MB` bound ingestion and storage. PostgreSQL stores the
normalized headers/body, UID identity, local read/archive state, omitted-file
explanations, and quarantine/cleanup audit records. Raw wire messages are not
retained after accepted content is persisted.

PDF viewing does not create a public or reusable share URL. The backend accepts
only a validated source UUID, rebuilds the expected immutable storage path,
and verifies the PDF signature, byte size, and SHA-256 content hash before
streaming. Responses use private no-store caching, content sniffing protection,
safe inline filenames, and browser `HEAD`/byte-range support. A missing,
changed, unreadable, or non-PDF file fails safely without returning the host
path, extracted text, directory contents, or another source's file. Keep the
application on a trusted local network as described above; anyone who can reach
this single-owner installation can reach its owner-facing API.

Use the Materials tab to remove a source safely. It deletes only the selected
`<source-id>` directory and its database rows, even if the raw file is already
missing. Use the course deletion dialog to remove an entire course directory.
Do not manually delete the storage root while the application is running. If
manual cleanup is necessary, stop the application, make both backups described
below, and remove only the exact course or source ID directory. The stale source
record can then be removed through the Materials tab.

## Data durability, relocation, backup, and restore

The stable installation identity, persistent/disposable data inventory,
legacy adoption procedure, supported `mv` workflows, rollback steps, and clean
restore instructions are documented in
[Data durability and recovery](docs/data-durability.md). Run the read-only
check at any time:

```bash
make data-preflight
```

It reports the resolved identity, PostgreSQL, Codex-auth, and
integration-secret volume names, course, mail, and document storage, backup root,
reachability, and other Compose database-volume
candidates without creating, copying, or deleting a missing volume.

### Coordinated backup

```bash
make backup
```

The command briefly stops frontend/backend write paths, keeps PostgreSQL
available for `pg_dump`, and restores only services that were previously
running. It writes a unique directory under `BACKUP_ROOT` (default
`./backups`) containing `database.dump`, `course-content.tar.gz`,
`mail-attachments.tar.gz`, `document-projects.tar.gz`, and `manifest.json`.
The manifest records the installation ID, UTC timestamp, byte
counts, and SHA-256 checksums. The command lists the PostgreSQL custom dump,
fully validates all private-file archives, verifies checksums, applies private
permissions, and only then reports success. No prior backup is overwritten.

The bundle contains private calendars/subscriptions, courses and original
uploads, notes/summaries, Inbox metadata/body and attachments, document
projects/tags/source, Assistant
history/proposals/citations, diagnostics, and audits. `backups/` is ignored by
Git. Copy complete bundle directories only
to encrypted, access-controlled storage.

ChatGPT and mailbox credentials are intentionally excluded. Reauthenticate and
reconnect the mailbox after a clean restore instead of copying renewable
tokens or app passwords.

### Restore

Restore only a complete directory produced by `make backup`. The command first
validates its manifest, sizes, checksums, archive paths, and PostgreSQL dump. It
then creates a new coordinated safety backup of the target. Confirmation must
exactly match the target identity shown by `make data-preflight`:

```bash
make restore \
  BACKUP=backups/20260831T120000Z-source-installation \
  CONFIRM_RESTORE=target-installation
```

The previous course, mail, and document directories are retained as
`course_content.before-restore-<timestamp>` and
`mail_attachments.before-restore-<timestamp>`, and
`document_projects.before-restore-<timestamp>`; the pre-restore bundle is the
database rollback. Migrations run before services resume. Verify Courses,
Calendar/subscriptions, Inbox/attachments, Documents/source hashes, Assistant history/citations,
diagnostics, and upload hashes. Sign in to ChatGPT and reconnect the mailbox
again if needed. A corrupt, mismatched, or unsafe bundle fails before the
active database or private file trees are changed.

Backups created by M20 before Documents existed remain restorable. Their
format-2 manifests create an empty document root while retaining any previous
target document directory as a rollback path.

## Safe error explanations

Handled API failures return a public error code and message plus opaque
`error_id` and `request_id` values. The persisted report contains only
allowlisted operation metadata, validation fields, relevant content type/size,
safe constraints, and a sanitized exception type. Passwords, mail bodies,
tokens, cookies,
authorization headers, request bodies, credentials, environment variables,
source paths, and unrelated files are redacted or never collected.

When a Materials error or failed Assistant job shows **Ask Assistant about this
error**, the backend starts an explanation-only Codex job from that stored
report. Failed Assistant jobs also show an owner-facing reason and recovery
steps plus expandable developer details containing the failure stage, safe
field-level validation issues, job ID, and diagnostic report ID. Raw model
output is intentionally not logged or exposed. The explanation result clearly
separates changes you can make to the input from possible future application
improvements and states whether retrying is safe. The runtime can suggest an
improvement, but it cannot inspect or edit application source code and never
claims a suggestion was implemented.

Sanitized reports and their audit records are retained with the owner database
and included in database backups; this phase has no separate diagnostic purge
UI. Temporary Codex workspaces are still deleted immediately after each job.

## Troubleshooting

- If a course-note question asks which course you mean, reply with the exact
  course name or course code. This is an intentional privacy boundary.
- If expected note context is missing, confirm that the course is active, the
  note contains the search term, and any slide range is linked to a Slides
  source with completed text extraction.
- If **Ask Assistant about this error** cannot generate an explanation, sign in
  again on the Assistant page and retry. The original operation is not repeated
  by the explanation action.
- If an Assistant reply is blocked as invalid, expand **Developer details** to
  see whether parsing, schema, citation, proposal-target, or recurrence checks
  rejected it. The Assistant has already made one automatic format-correction
  attempt; retry manually or rephrase the request. If it repeats, use the
  job/report ID to trace it without sharing raw private conversation data.
- If an error report cannot be found, it may belong to another restored database
  or installation. Repeat the failing operation to create a new sanitized
  report; do not paste credentials, `.env`, logs, or private files into chat.
- After restoring a database, run `make migrate` and check `make logs` for an
  Alembic error before using the app. Restore the matching course-content
  archive when source rows exist.
- A report ID is safer than raw logs, but diagnostic reports are still private
  owner data. Do not publish database dumps or diagnostic API responses.

## Privacy-safe logging

HTTP access logging is disabled because event searches and device-login paths
can contain private values. Application failures log opaque record IDs and error
types, not calendar content, ICS URLs, model output, credentials, or request
bodies. Keep Docker logs private and review them before sharing.

Runtime Codex workspaces are private temporary directories containing one of:
bounded calendar/course context selected for the question, one note body plus
its explicitly linked slide text, one current editor draft for Prettify, or one
sanitized error report. Prettify and diagnostic workspaces never contain
calendars or course files. Tools, network access, repository access, source
editing, and host filesystem access are disabled; each workspace is deleted
immediately after the job.
Mail headers, bodies, attachments, IMAP health responses, and mailbox
credentials are never added to runtime Codex workspaces in this milestone.
