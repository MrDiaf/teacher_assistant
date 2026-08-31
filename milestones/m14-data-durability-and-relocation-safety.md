# M14 — Data durability, relocation, and update safety

- [x] This milestone

## Outcome

Audit every category of persistent owner data, reproduce repository move and
update scenarios, and remediate any path that can make data disappear or appear
lost. After this milestone, moving or renaming the complete project directory
with `mv`, rebuilding containers, and applying normal source updates must retain
the installation's data when the documented procedure is followed.

This milestone is first because all later features create or depend on private
owner data.

## Planning risk (remediated by this milestone)

At planning time, Compose stored PostgreSQL and Codex authentication in named
volumes. Unless a stable Compose project name is explicitly preserved, Docker
Compose derives their names from the project directory or invocation context.
A move or rename that changes that identity can attach new empty volumes. The
old volumes may still exist, but the application can look as though its data was
deleted.

Course uploads used the repository-relative bind mount
`./data/course_content`. Moving the entire directory preserves those files, but
copying only tracked Git files does not because `data/` is intentionally
ignored. Database and course-file backups were separate, and the default
database backup filename was overwritten by the next backup.

These observations are not permission for an ad-hoc volume rename or copy. The
implementation must begin with a read-only inventory and a recoverable migration
plan for existing installations.

## Persistent-data inventory

The audit must account for at least:

- PostgreSQL records: calendars, events, subscriptions, courses, notes, slide
  links, extracted text, summaries, conversations, proposals, citations,
  diagnostics, audits, and job state;
- original uploaded course files under `COURSE_STORAGE_ROOT`;
- private `.env` installation configuration;
- the Codex/ChatGPT authentication volume, while continuing to allow safe
  reauthentication instead of copying credentials into backups;
- any other Docker volume or host path found during implementation;
- browser-only UI state planned for M19, documented as convenience state rather
  than authoritative application data.

Temporary runtime workspaces, build artifacts, caches, test databases, and
`node_modules` are not owner data and must remain disposable.

## Supported safety scenarios

Test and document all of these separately:

1. `make down`, move the complete repository to another parent directory with
   the same final directory name, then `make dev`.
2. `make down`, rename the repository directory with `mv`, then `make dev`.
3. Rebuild the application with `make dev` after source changes.
4. Apply database migrations with `make migrate`.
5. Run `make down` and `make restart` without volume deletion.
6. Restore the database and matching course files into a clean installation.
7. Keep two separate clones on one host without sharing data accidentally.

Moving a running installation is not supported. The documented relocation
procedure must stop application writes first and must include hidden files such
as `.env`.

## Required durability design

- Give every installation a stable, explicit data namespace that survives a
  directory rename while remaining configurable and unique for multiple clones.
- Preserve compatibility with the current default volumes or provide a
  preflighted one-time migration that finds and verifies them.
- Add a read-only data preflight command that reports the resolved installation
  identity, database volume, Codex-auth volume, course storage root, and whether
  expected data is reachable.
- Refuse ambiguous migration when both an old and a new location contain data;
  explain the choices without deleting either copy.
- Never silently initialize a fresh database when the preflight finds evidence
  that the installation previously used another data namespace.
- Never use `docker compose down -v` for normal development, update, move, or
  migration commands. Test/E2E cleanup may delete only its explicitly isolated
  test volumes.
- Ensure source updates and image rebuilds do not overwrite `.env`, database
  data, uploads, or backups.
- Preserve per-installation isolation; a fixed global volume name shared by all
  clones is not acceptable.

The exact implementation may use a stable `COMPOSE_PROJECT_NAME`, explicit
volume names, a host data root, or another Docker-compatible design, but it must
satisfy relocation, existing-installation migration, and multi-clone tests.

## Backup and recovery requirements

- Create a coordinated backup command that records a PostgreSQL dump and course
  files together with a manifest, timestamps, and checksums.
- Use unique backup names rather than overwriting the only known-good backup.
- Restrict backup permissions and keep backups ignored by Git.
- Validate that the database dump can be listed/restored and that the course
  archive checksum matches before calling a backup successful.
- Document that Codex authentication is renewable and may require sign-in after
  restore; never place tokens in a normal data archive.
- Provide a rollback path before changing any existing volume or mount.
- Never delete the old volume/data directory automatically after migration.
  Cleanup is a later explicit owner action after verification.

## Completed checklist

- [x] Inventory every persistent and disposable data location.
- [x] Record the current resolved Compose project and volume names.
- [x] Reproduce same-name moves, directory renames, rebuilds, and migrations
  using non-private fixture data.
- [x] Implement a stable per-installation data identity.
- [x] Add a non-destructive migration/preflight path for existing volumes.
- [x] Add coordinated, versioned database-and-course-file backups with a
  manifest and checksums.
- [x] Add a read-only data-safety/preflight Make target.
- [x] Verify normal Make targets never delete owner volumes.
- [x] Add automated Compose/config checks and integration coverage where
  practical.
- [x] Perform a documented end-to-end relocation and restore drill.
- [x] Update `.env.example`, `Makefile`, `README.md`, and `handoff.md`.
- [x] Verify Calendar, Courses, Assistant history, uploads, and Codex sign-in
  behavior after relocation/update.

## Verification record — 2026-08-31

- The current installation explicitly resolves to Compose project
  `teacher_assistant`, database volume `teacher_assistant_database-data`, and
  Codex-auth volume `teacher_assistant_codex-auth-data`. Its host course root is
  the configured project-relative `data/course_content` directory.
- `make data-preflight` found both the selected installation and another
  populated legacy candidate. Adoption explicitly selected the active source;
  the other candidate was not mounted, copied, merged, or deleted.
- `make data-relocation-test` passed with non-private fixtures. It verifies a
  stopped same-final-name parent move, a stopped directory rename, rebuild,
  migration, stable database IDs/counts, uploaded-file hash, auth-volume marker,
  different-clone isolation, coordinated backup/clean restore, corrupt bundle
  rejection before mutation, legacy volume copy/digest verification, retained
  source volumes, and populated-target ambiguity refusal.
- `make backup` produced a unique permission-restricted bundle, and both
  `pg_restore -l` and full manifest/archive validation passed before success.
- The adopted live installation retained its uploaded-file aggregate hash,
  reached Alembic `20260731_0017 (head)`, returned healthy backend/frontend
  responses, and reported its existing ChatGPT authentication as connected
  after adoption, migration, rebuild, and restart.
- `make test` passed with 114 backend and 39 frontend tests; `make e2e` passed
  all 8 Playwright/accessibility tests; `make lint`, the frontend production
  build, Docker startup, and `git diff --check` passed.

## Acceptance criteria

- A fixture installation containing at least one calendar/event, ICS
  subscription, course, note, summary, Assistant conversation/proposal,
  diagnostic record, and uploaded PDF retains the same IDs, counts, and file
  hashes after both supported `mv` scenarios.
- Rebuilding and migrating retain the same fixture data.
- Existing installations can adopt the stable identity without destructive
  commands, and rollback remains possible until the owner verifies success.
- Two clones configured as different installations cannot attach each other's
  database, uploads, or Codex-auth volume.
- A backup and clean restore reproduce database records and uploaded-file
  hashes; a mismatched or corrupt archive fails clearly.
- No private fixture data, `.env`, database files, uploads, tokens, or backups
  are added to Git.
- Relevant tests, Docker startup, health checks, migrations, and
  `git diff --check` pass.

## Expected implementation areas

```text
compose.yml
compose.dev.yml
.env.example
Makefile
.gitignore
README.md
scripts or containerized maintenance helpers, if needed
backend tests or isolated integration checks
```

Do not begin M15 until M14 is verified and its checkbox is checked.
