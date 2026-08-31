# Data durability and recovery

Teacher Assistant has one private data namespace per installation. The value
of `COMPOSE_PROJECT_NAME` in `.env` is the stable installation identity. Docker
Compose derives these persistent volume names from it:

```text
<installation-id>_database-data
<installation-id>_codex-auth-data
```

The ID does not depend on the repository directory after initialization. A
complete directory move or rename reconnects the same volumes on the same
Docker host. Different clones must use different IDs.

## Data inventory

Authoritative or private installation data:

- PostgreSQL in `<installation-id>_database-data`: calendars, events, ICS
  subscriptions, courses, material metadata and extracted text, notes and slide
  links, summaries, Assistant conversations/jobs/proposals/citations/context
  audits, diagnostic records/audits, and migration state;
- original Literature and Slides files at host `COURSE_DATA_DIR` (default
  `./data/course_content`), mounted at `COURSE_STORAGE_ROOT` in the backend;
- private configuration in `.env`, including the stable Compose project name;
- renewable ChatGPT/Codex credentials in
  `<installation-id>_codex-auth-data`;
- coordinated backups below `BACKUP_ROOT` (default `./backups`);
- `.teacher-assistant-installation`, a non-secret local guard recording which
  database volume has already been initialized.

Browser-only state planned for M19 is convenience state, not authoritative
application data. It will not replace PostgreSQL or require server backup.

Disposable data includes runtime Codex workspaces, Python/Node caches,
`node_modules`, frontend build output, images/containers, the development
`frontend-node-modules` volume, logs, and explicitly isolated test/E2E volumes.
Runtime workspaces continue to be removed immediately after each job.

The Git ignore rules cover `.env`, the installation marker, `data/`,
`backups/`, runtime directories, caches, and logs. Never add private data to
Git.

## Read-only preflight

Run before an update, migration, move, backup, or restore:

```bash
make data-preflight
```

It reports the resolved installation ID and identity source; exact database and
Codex-auth volume names and reachability; host course-storage and backup paths;
recorded initialization state; and other Compose `database-data` candidates.
The check does not create a missing volume.

A nonzero result means adoption, initialization, or recovery is required.
Data-changing `make dev`, `make restart`, `make migrate`, `make backup`, and
`make restore` are guarded. Once the local marker says a database was
initialized, a missing or invalid database volume stops those commands instead
of silently creating an empty replacement. Read-only source checks and logs
remain available for diagnosis.

## New installations and separate clones

The normal first start remains:

```bash
cp .env.example .env
make dev
```

`make dev` replaces `teacher-assistant-change-me` with a random stable ID and
records the installation marker before Docker creates volumes. If the current
directory-derived legacy name already has PostgreSQL data, initialization
stops and requires explicit adoption.

To select a readable unique name for a second clone:

```bash
cp .env.example .env
make data-init INSTALLATION_ID=teacher-assistant-study
make dev
```

Use a distinct ID, repository directory, `COURSE_DATA_DIR`, ports, and backup
root per clone. Different IDs resolve different database, Codex-auth, network,
container, image, and disposable development volumes. Default relative course
and backup paths are isolated by clone.

## Adopt an existing pre-M14 installation

Do not change volume names by hand and do not overwrite the existing `.env`.

1. Stop writes and inspect without volume deletion:

   ```bash
   make down
   make data-preflight
   ```

2. Select the exact legacy Compose project from the report. If it was
   `teacher_assistant`, the least disruptive adoption pins that same value:

   ```bash
   make data-adopt \
     LEGACY_PROJECT=teacher_assistant \
     INSTALLATION_ID=teacher_assistant
   ```

   To change to another unique ID, set `INSTALLATION_ID` accordingly. The
   command requires stopped source containers, verifies the PostgreSQL source,
   refuses a populated target, copies database and renewable-auth volumes, and
   compares content digests.

3. Run `make data-preflight`, then `make dev`. Verify Calendar/ICS
   subscriptions, Courses/notes/summaries/uploads, Assistant history/proposals,
   diagnostics, and ChatGPT sign-in state.

Rollback metadata is saved privately below
`backups/migrations/<timestamp>-<source>-to-<target>/`. Existing source volumes
are never deleted. If both source and target contain data, adoption refuses to
merge or choose between them.

### Adoption rollback

Keep the application stopped. Restore `env.before` and
`installation-state.before` from the migration directory when present. For a
legacy adoption with no previous marker, move the new
`.teacher-assistant-installation` into that migration directory. The source
database/auth volumes listed in `migration-record.txt` remain intact; inspect
and read-only mount them before starting. Never delete the copied target until
the source namespace is verified. Old-volume cleanup is a separate explicit
owner action and is not performed by M14 commands.

## Supported move and rename procedure

Moving a running installation is not supported.

1. Run `make data-preflight` and `make backup`.
2. Run `make down`; it removes containers/network, never owner volumes.
3. Move the complete project directory with `mv`. Include hidden `.env` and
   `.teacher-assistant-installation`, ignored `data/`, and ignored `backups/`.
   Copying only Git-tracked files is not a data move.
4. In the new directory, run `make data-preflight`.
5. Run `make dev`, then `make migrate` when an update includes migrations.
6. Verify application health and owner data before cleanup.

These steps support a same-final-name parent move and a final-directory rename.
They also support ordinary source updates and rebuilds: builds do not overwrite
`.env`, named volumes, `COURSE_DATA_DIR`, or `BACKUP_ROOT`.

Normal `make down` and `make restart` never request volume deletion. Only test
and E2E projects with explicit isolated identities use volume cleanup. Never
use `docker compose down -v` for an installation.

## Coordinated backups

```bash
make backup
```

The command pauses backend/frontend writes, dumps PostgreSQL in custom format,
archives the matching course tree, and writes a unique UTC-stamped bundle:

```text
backups/<UTC timestamp>-<installation-id>/
├── database.dump
├── course-content.tar.gz
└── manifest.json
```

The manifest contains SHA-256 hashes and byte counts. Success is reported only
after `pg_restore` lists the dump and the course archive passes checksum,
entry-type, path, and full-read validation. Directories use `0700`; files use
`0600`. Previously running services resume.

Codex authentication is excluded. It is renewable and should be recreated with
**Sign in with ChatGPT** instead of copied into an archive.

## Clean restore and rollback

Initialize a clean target with a unique ID and start it once. Run
`make data-preflight`, then:

```bash
make restore \
  BACKUP=/secure/path/20260831T120000Z-source-id \
  CONFIRM_RESTORE=target-installation-id
```

Before changing the target, restore validates the complete bundle and creates a
new coordinated safety backup. It stops writes, recreates and loads the target
database with `--exit-on-error`, safely extracts course files, runs migrations,
and resumes previously running services. The prior course directory remains as
`course_content.before-restore-<UTC timestamp>`. Keep it and the pre-restore
bundle until verification.

A missing component, size/checksum mismatch, unreadable PostgreSQL dump,
duplicate/traversal archive path, symlink, device file, or unsupported manifest
fails clearly. Bundle validation happens before replacement. If a later host or
disk error interrupts restore, services remain stopped and the printed safety
backup plus course rollback directory provide recovery.

After restore, verify database record IDs/counts, source hashes, Calendar and
subscriptions, Courses and summaries, Assistant history/proposals, diagnostics,
and Alembic head. Sign in to ChatGPT again when the target auth volume has no
renewable session.

## Verification command

Maintainers can run the non-private isolated drill:

```bash
make data-relocation-test
```

It creates fixture installations containing a calendar/event, ICS subscription,
course/upload, note/slide link, summary, Assistant conversation/proposal,
citation/context audit, and diagnostic audit. It verifies IDs/counts and hashes
across migrate/rebuild, same-name parent move, directory rename, coordinated
backup, clean restore, two-clone isolation, corrupt-archive rejection, legacy
volume adoption/copy verification, and populated-target ambiguity refusal.
Cleanup targets only its random `m14-*` projects and temporary directory.
