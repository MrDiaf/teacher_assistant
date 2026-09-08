# M21 — Durable Documents foundation and project overview

- [x] This milestone

## Outcome

Add a new **Documents** module for private LaTeX projects, with searchable and
tagged project management plus recoverable source storage. This milestone does
not add the multi-file editor, compilation, PDF preview, or Codex advice.

M19 and M20 must be complete first unless the owner explicitly changes the
planned milestone order. Planning this milestone does not make it active.

## Product boundary

Documents is a separate top-level module, not a Course material type. Place it
after the planned Inbox entry and before Study Plan while preserving the
existing Teacher Assistant shell and responsive navigation.

The overview is inspired by the useful parts of an Overleaf project list:

- project title and last-modified time;
- search by project title;
- multiple colored tags per project;
- tag creation, assignment, removal, and filtering;
- open, rename, source-download, and delete actions;
- clear empty, loading, and failure states.

Do not add owner columns, registration, sharing, collaboration, upgrade
prompts, public profiles, or organization features. This remains one owner's
private installation. A favorite/star marker is not part of this milestone;
"marking" a project means applying one or more tags.

## Metadata and ownership

Use PostgreSQL for document metadata, not source bodies. The durable model must
include at least:

- a UUID document-project ID;
- title, created timestamp, and updated timestamp;
- one or more optional tag associations;
- tag name and owner-selected color;
- enough storage identity to reconstruct the expected private directory
  without accepting a path from the browser.

Tag names are trimmed, bounded, and unique under a documented case-normalized
rule. Deleting a tag removes only its associations and never deletes a project
or source file. Project titles need not be unique because UUIDs are the stable
identity.

Do not add an owner, user, tenant, team, or organization column.

## Private source storage

Add a configurable document storage root, with a host default such as
`./data/document_projects` and a separate container path. Store each project
under its immutable UUID rather than its editable title:

```text
data/document_projects/
└── <project-id>/
    ├── source/
    │   └── main.tex
    └── build/
```

`source/` contains owner-authored project files. `build/` is reserved for
verified derived artifacts introduced in M23. A new project starts with a
small valid `main.tex`, but M21 manages only that initial root file.

The storage service must:

- derive every path from the configured root and validated project UUID;
- reject absolute paths, parent traversal, symlinks, hard-link surprises,
  devices, sockets, and non-regular source files;
- create private directories and files with restrictive permissions;
- use temporary files plus atomic replacement for source writes;
- coordinate database and filesystem creation without leaving an apparently
  valid project whose source directory is missing;
- quarantine the exact UUID directory before a confirmed project deletion,
  restore it if the database transaction fails, and purge only after success;
- never return a physical server path or directory listing outside the exact
  validated project.

Manual host access is a recovery path, not a second live editing interface.
Documentation must tell the owner to stop application writes before copying or
inspecting raw source folders.

## API and download behavior

Keep routes, application service, repository, and filesystem storage separate.
Provide bounded endpoints for:

- listing, searching, creating, reading, renaming, and deleting projects;
- listing, creating, updating, deleting, assigning, and unassigning tags;
- downloading the current `main.tex` as an attachment;
- downloading a generated ZIP containing only the project's current source
  tree.

Downloads resolve through project IDs. ZIP entries must be root-relative,
portable, bounded, deterministic where practical, and protected from absolute
paths, `..`, symlinks, special files, duplicate names, and archive bombs. Do
not include database metadata, server paths, future build files, compiler logs,
credentials, or another project's content.

Project deletion is a manual owner action with an explicit confirmation naming
the project and explaining that source files will be removed. Codex has no
document-delete action.

## Durability, backup, and Git safety

Document source is authoritative private owner data from the first successful
project creation. In this milestone:

- extend `make data-preflight` to resolve and report document storage;
- include the complete document source tree in coordinated backups;
- add manifest sizes and SHA-256 checksums for the document archive;
- validate every archive entry before restoring anything;
- restore database metadata and matching document files together;
- preserve the old target document directory as a rollback path;
- extend relocation, clean-restore, corruption, and two-clone isolation tests;
- keep document storage, source downloads, and backups ignored by Git;
- never include Codex credentials in the document archive.

M14's ambiguity and non-destructive adoption rules continue to apply. Do not
silently attach another clone's document directory or delete legacy data.

## Milestone checklist

- [x] Add the Documents module to the application shell without changing the
  existing module design.
- [x] Extend the versioned M19 module preference to accept Documents safely.
- [x] Add document-project and tag models, migration, schemas, repository, and
  service boundaries.
- [x] Add private UUID-based source storage with atomic creation and deletion.
- [x] Add the project overview, search, tag filters, and accessible project
  actions.
- [x] Add safe `main.tex` and complete-source ZIP downloads.
- [x] Add explicit project-deletion confirmation and exact-directory
  quarantine behavior.
- [x] Add document storage to preflight, backup, restore, relocation, and
  multi-clone isolation.
- [x] Add backend, frontend, storage, archive, accessibility, and end-to-end
  tests.
- [x] Update `.env.example`, Compose configuration, `README.md`, data-durability
  documentation, and `handoff.md` only for behavior actually implemented.

## Acceptance criteria

- The owner can create, find, rename, tag, open, and delete a private document
  project from the Documents overview.
- A project can have several tags, and one tag can classify several projects.
- Search and tag filters compose predictably and show readable empty states.
- A newly created project has a recoverable `main.tex` beneath the documented
  private host root.
- The overview can download that `.tex` file and a source-only ZIP without
  exposing a host path or another project.
- Invalid UUIDs, guessed paths, traversal, symlinks, malformed archives, and
  database/storage disagreement fail safely.
- A coordinated backup and clean restore reproduce project/tag records and
  exact source hashes.
- Moving or renaming the stopped installation retains document records and
  source files under the stable installation identity.
- Existing Calendar, Courses, Assistant, Inbox behavior, read-only rules, and
  M19 state validation remain intact.
- Relevant tests, Docker startup, migrations, lint, production build, E2E,
  relocation checks, and `git diff --check` pass.

## Expected implementation areas

```text
backend/alembic/versions/
backend/app/documents/models.py
backend/app/documents/schemas.py
backend/app/documents/repository.py
backend/app/documents/service.py
backend/app/documents/storage.py
backend/app/documents/routes.py
backend/app/core/config.py
backend/app/main.py
backend/app/maintenance/data_archive.py
backend/tests/
frontend/src/App.tsx
frontend/src/components/AppShell.tsx
frontend/src/features/documents/
frontend/src/styles.css
frontend tests and e2e/tests/
compose.yml and isolated test Compose files
scripts/data-*.sh and data-safety tests
.env.example
.gitignore
README.md
docs/data-durability.md
handoff.md
```

Do not begin M22 until this milestone's durability and recovery acceptance
criteria are verified.
