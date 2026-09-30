# M22 — Relative LaTeX file tree and source editor

## Objective

Turn an M21 document project into an Overleaf-inspired source workspace with a
relative file tree and an established LaTeX-aware code editor. Source files are
saved to the project's durable `source/` folder. This milestone still does not
compile LaTeX or produce a PDF.

## Dependencies

Requires M21 and the inserted M21A-M21I refactoring sequence to be complete
because this milestone extends Documents through the public entries,
module-owned styles, and focused verification that sequence establishes.
Inspect the resulting repository state first; read
[M21I](m21i-modular-verification-and-cutover.md) only if additional intent is
required.

This milestone is planned, not active, until the owner selects it.

## Existing-state check

Before making changes:

1. Inspect the relevant repository state.
2. Evaluate every completion criterion below.
3. Mark criteria that are already satisfied, here and in
   [PLAN.md](../../PLAN.md).
4. Run the smallest relevant verification when necessary.
5. If every criterion is already satisfied, mark the milestone complete and
   make no implementation changes.
6. Otherwise, preserve existing correct work and implement only what is missing.

Do not read other milestone files unless they are necessary to resolve
information that cannot be determined from the repository or current
instructions.

## Scope

Resolve these starting-point paths through the module ownership index produced
by M21A-M21I. Extend Documents public entries and its own styles/tests; do not
restore direct shell wiring, foreign internals, or global feature CSS. Preserve
module-state enforcement and focused/full verification introduced by refactoring.

```text
backend/app/documents/file_schemas.py
backend/app/documents/file_service.py
backend/app/documents/storage.py
backend/app/documents/routes.py
backend/tests/test_document_files.py
frontend/package.json and lockfile
frontend/src/features/documents/DocumentEditor.tsx
frontend/src/features/documents/DocumentFileTree.tsx
frontend/src/features/documents/LatexSourceEditor.tsx
frontend/src/features/documents/api.ts
frontend/src/features/documents/types.ts
frontend/src/features/documents/*.test.tsx
Documents-owned stylesheet established in M21C
e2e/tests/
README.md
handoff.md
```

Not authorized:

- Compiling LaTeX or producing a PDF (M23).
- Autocomplete, language servers, visual/WYSIWYG editing, section outlines, and
  refactoring.
- ZIP import and folder-upload shortcuts.
- Overleaf branding, collaboration controls, menus, history, share buttons,
  visual editing, account controls, or subscription prompts.

Stop after verification. Do not begin M23 until source persistence, relative
paths, conflict protection, and recovery are verified; M23 requires explicit
owner selection.

## Required work

### Owner workflow

```text
Owner opens Documents
    -> opens a project
    -> sees a root-relative file tree and source editor
    -> creates folders or uploads source/images
    -> opens and edits a text source
    -> server-backed autosave reports Saving, Saved, or Failed
    -> selects the project's main .tex file
    -> downloads main.tex or the complete source project when needed
```

The desktop layout should reserve a left pane for the file tree and a large
center pane for source. M23 will add the right-side PDF pane. On narrower
screens, use accessible pane tabs or toggles instead of forcing an unusable
three-column layout.

Do not copy Overleaf branding, collaboration controls, menus, history, share
buttons, visual editing, account controls, or subscription prompts.

### Established editor dependency

Use CodeMirror 6 and its maintained LaTeX/sTeX language support. Do not build a
custom source editor, syntax engine, caret model, or undo stack. Preserve
native copy/paste and accessible keyboard behavior and expose a plain-text
fallback if the enhanced editor cannot initialize.

The initial editor provides source highlighting, line numbers, selection,
search, undo/redo, and common indentation behavior. Autocomplete, language
servers, visual/WYSIWYG editing, section outlines, and refactoring are outside
this milestone.

### Relative project tree

Every API-visible file path is a normalized POSIX path relative to the
project's `source/` root. The UI must show the same root-relative path used by
LaTeX. If the tree contains `images/diagram.png`, source in root `main.tex`
refers to it as `images/diagram.png`.

Support:

- nested folders;
- UTF-8 text sources such as `.tex`, `.bib`, `.sty`, `.cls`, `.bst`, `.bbx`,
  `.cbx`, `.clo`, `.def`, and `.txt`;
- verified `.pdf`, `.png`, `.jpg`, and `.jpeg` image assets;
- creating, uploading, opening, saving, renaming, moving, and deleting files;
- creating, renaming, moving, and explicitly deleting folders;
- selecting exactly one existing `.tex` file as the main document.

Reject executable files, devices, sockets, archives, hidden compiler control
files, `.latexmkrc`, project-supplied build scripts, and unsupported file
types. ZIP import and folder-upload shortcuts are outside this milestone; the
owner creates folders and uploads bounded files through the application.

### Path and storage validation

The backend is authoritative for every file operation. It must:

- reject absolute paths, empty segments, `.`, `..`, backslashes, NUL/control
  characters, normalization collisions, reserved internal directories, and
  paths that resolve outside `source/`;
- bound segment length, total path length, nesting depth, file count,
  individual upload size, and total project size;
- validate text as UTF-8 without silently replacing bytes;
- validate image signatures rather than trusting the extension or browser MIME
  type;
- refuse symlinks, hard links to unexpected inodes, and non-regular files when
  resolving, scanning, downloading, moving, or deleting;
- use temporary files and atomic replacement so a failed save retains the last
  complete stored version;
- lock or serialize conflicting path mutations within one project;
- prevent deleting or renaming the selected main file until another valid
  `.tex` file is selected, or update that selection atomically;
- never expose an absolute host/container path.

Define conservative configurable limits during implementation and document
their defaults. At minimum, tests must cover 1,000-file projects, 20 path
segments, a 25 MiB individual asset, and a 250 MiB total project boundary
without requiring those values to be raised silently.

### Save and conflict behavior

Source content is authoritative on the backend, not in browser storage. Use
server-backed autosave with a short debounce and visible state. Each loaded
text file carries a revision, content hash, or equivalent concurrency token.

- Save only the current file and expected revision.
- A stale browser tab receives a conflict and cannot overwrite newer content.
- A failed save leaves the backend copy unchanged and preserves the visible
  editor draft for retry or manual copying.
- Navigating away waits for or clearly warns about an unsaved/failed write.
- Binary files are never decoded into the text editor.
- Do not put complete LaTeX projects, images, or authoritative file contents in
  `localStorage`.

The M21 source ZIP must include the complete current nested tree after M22, but
must still exclude build artifacts and internal metadata.

### Work order

1. Add CodeMirror 6 with maintained LaTeX/sTeX highlighting and an accessible
   plain-text fallback.
2. Add project-editor routing/state without creating a second application
   shell.
3. Add validated root-relative file and folder APIs through a document-file
   service and storage boundary.
4. Add the accessible file tree, breadcrumbs, active-file state, and main
   document marker.
5. Add safe text-file creation, upload, autosave, rename, move, and delete.
6. Add verified image upload, file-size display, and non-text handling.
7. Add revision-based stale-write protection and recoverable save failures.
8. Expand source ZIP downloads to the complete nested source tree.
9. Add storage quotas and clear limit/error states.
10. Add traversal, symlink, normalization, MIME, stale-write, and atomic-save
    tests.
11. Add frontend keyboard, focus, responsive, accessibility, and E2E tests.
12. Update owner documentation for relative paths, supported files, saving,
    and raw-source recovery.

## Completion criteria

- [ ] The owner can build a nested LaTeX source tree and edit multiple UTF-8
  source files without leaving Teacher Assistant.
- [ ] Root-relative paths shown in the tree match the paths the future compiler
  will use.
- [ ] A project containing `main.tex`, `chapters/introduction.tex`, and
  `images/diagram.png` preserves those exact relative relationships through
  save, reopen, ZIP download, backup, and restore.
- [ ] Autosave reports its actual state and never claims a failed write
  succeeded.
- [ ] A stale tab cannot silently overwrite a newer revision.
- [ ] Invalid paths, unsupported files, spoofed images, symlinks, and quota
  overflows fail without corrupting existing source.
- [ ] The main-document selection always names an existing `.tex` file.
- [ ] Keyboard and screen-reader users can navigate the tree, open a file, edit,
  save, and recover from an error.
- [ ] Existing Documents overview, backup, deletion, and all earlier modules
  remain intact.
- [ ] Relevant backend, frontend, storage, E2E, lint, build, Docker, and
  `git diff --check` checks pass.

## Verification

This milestone stays inside Documents, so prefer the focused Documents target
and broaden only for the shared pieces it touches (frontend dependencies,
source ZIP, coordinated backup/restore).

- Focused Documents backend, frontend, and browser tests
  (`make test-module MODULE=documents`), including traversal, symlink,
  normalization, MIME, stale-write, atomic-save, quota, keyboard, focus,
  responsive, and accessibility cases.
- The 1,000-file, 20-segment, 25 MiB asset, and 250 MiB project boundary tests.
- Backup and restore of a nested project (`make data-relocation-test`).
- `make lint` and the frontend production build, because a frontend dependency
  is added.
- Docker startup.
- `git diff --check`.
