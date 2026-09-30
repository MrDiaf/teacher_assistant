# M23 — Isolated LaTeX compilation and PDF preview

## Objective

Compile the saved main document with a mature LaTeX distribution, show a PDF
beside the source editor, and let the owner download the latest successful PDF
from either the editor or project overview. Compilation runs in a separately
isolated worker and has a per-project owner-adjustable timeout.

## Dependencies

Requires M22 to be complete because compilation snapshots the committed source
revisions and root-relative main file that M22 introduces. M22 includes the
prerequisite M21A-M21I refactoring gate. The compiler remains a separately
isolated worker within the approved modular-monolith architecture. Inspect the
resulting repository state first; read
[M22](m22-relative-latex-editor.md) only if additional intent is required.

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

Resolve these starting-point paths through the completed module ownership map.
Register Documents compiler lifecycle/capabilities through public entries, use
module-owned styles/tests, and preserve enable/disable and coordinated recovery
behavior. The worker's Compose configuration reuses root conventions without
giving the application or browser access to Docker management.

```text
latex_compiler/Dockerfile
latex_compiler/worker.py or an equivalent non-shell worker entrypoint
backend/alembic/versions/
backend/app/documents/compilation_models.py
backend/app/documents/compilation_schemas.py
backend/app/documents/compilation_repository.py
backend/app/documents/compilation_service.py
backend/app/documents/compiler_adapter.py
backend/app/documents/routes.py
backend/app/documents/storage.py
backend/app/core/config.py
backend/app/core/errors.py
backend/tests/
frontend/src/features/documents/DocumentEditor.tsx
frontend/src/features/documents/DocumentPdfPreview.tsx
frontend/src/features/documents/CompileControls.tsx
frontend/src/features/documents/api.ts
frontend/src/features/documents/types.ts
Documents-owned stylesheet established in M21C
frontend tests and e2e/tests/
compose.yml, compose.dev.yml, and isolated test Compose files
Makefile
.env.example
README.md
docs/data-durability.md
handoff.md
```

Not authorized:

- A TeX parser, layout engine, dependency resolver, bibliography pass, or PDF
  generator implemented by Teacher Assistant.
- XeLaTeX, LuaLaTeX, custom engines, project-controlled commands, and dynamic
  package installation.
- Codex compilation-error advice (M24).

Stop after verification. Do not begin M24 until isolation, timeout enforcement,
revision safety, and PDF integrity are verified with the real compiler
container; M24 requires explicit owner selection.

## Required work

### Compiler decision

Use a pinned TeX Live distribution with `latexmk`. Teacher Assistant must not
implement a TeX parser, layout engine, dependency resolver, bibliography pass,
or PDF generator.

The initial supported engine is pdfLaTeX. `latexmk` controls the necessary
repeat passes and available BibTeX/Biber work within the fixed offline package
set installed in the compiler image. XeLaTeX, LuaLaTeX, custom engines,
project-controlled commands, and dynamic package installation are outside this
milestone.

Build the compiler image reproducibly and document its TeX Live/latexmk
versions and installed package set. Updating that toolchain is an explicit
tested source change, not a runtime download.

### Compilation boundary

Do not install or invoke TeX Live inside the FastAPI process. Add a dedicated
compiler worker with no published port and no Docker-socket access. A bounded
filesystem-backed job queue on a dedicated volume may connect the backend and
worker without attaching the compiler to the application network.

For each compile request:

1. Finish or reject any pending autosave and select a committed source
   revision.
2. Create a private job ID and snapshot only that project's `source/` tree into
   a disposable job directory.
3. Record the validated root-relative main `.tex` path, source revision,
   timeout, and hardcoded compiler mode in a backend-owned manifest.
4. Let the offline worker compile from the snapshot's project root so
   `\input`, bibliography files, and graphics use normal root-relative paths.
5. Capture bounded output, exit status, elapsed time, and the expected PDF.
6. Have the backend validate the result before copying a successful PDF into
   the project's durable `build/` directory.
7. Remove the disposable job and auxiliary compiler files under a documented
   immediate/expiry cleanup rule.

The live `source/` directory is never mounted in the compiler and compilation
can never mutate owner source. The worker sees no repository, database,
course-storage, Inbox data, Codex authentication, `.env`, host home, Docker
socket, or other document project.

### Compiler sandbox

Defense in depth must include:

- `network_mode: none` or an equivalent verified no-network runtime;
- a non-root user, read-only root filesystem, dropped capabilities,
  no-new-privileges, bounded PIDs, CPU, memory, temporary storage, output size,
  and file descriptors;
- only the disposable job volume writable;
- TeX shell escape disabled, including TeX Live's restricted shell commands;
- no custom `latexmkrc`, initialization file, environment-provided command,
  arbitrary executable, or browser-supplied compiler flag;
- a minimal allowlisted environment and fixed working directory;
- process-group termination so a timeout kills compiler children as well as
  the parent;
- cleanup of abandoned queued/running jobs after backend or worker restart.

Source and compiler output are untrusted data. Do not execute a command copied
from a `.tex` comment, compiler log, API request, or later Codex response.

### Job and timeout model

Persist compile-job metadata with at least:

- project ID and committed source revision;
- `queued`, `running`, `succeeded`, `failed`, or `timed_out` status;
- effective timeout, start/finish timestamps, elapsed time, and safe exit
  classification;
- bounded sanitized log and latest successful PDF metadata/hash where
  applicable.

The owner can set a per-project compilation timeout from the Documents editor.
Use a documented default of 60 seconds and allow 10–600 seconds unless the
installation administrator configures a lower hard ceiling. Validate the value
in the UI, API schema, service, worker manifest, and worker. This is separate
from `CODEX_TIMEOUT_SECONDS` and must not change AI runtime limits.

Queue waiting time and actual compiler runtime must be displayed separately or
defined clearly. The compilation deadline applies to the compiler process,
while abandoned queue jobs have a separate bounded expiry.

### Logs and revision safety

Retain only a bounded owner-visible log, with a proposed maximum of 1 MiB after
normalization. Replace private temporary absolute paths with root-relative
project paths and mark truncation visibly. Never write source bodies, compiler
logs, project titles, or PDF content to ordinary Docker/application logs.

A compile is tied to the exact saved source revision. If source changes while a
job runs, the result may remain available as that revision's result but must be
labelled stale and must not be presented as the current source's PDF.

A failed or timed-out compile never replaces the last successful PDF. The UI
must identify the timestamp/revision of any older successful PDF instead of
implying that it came from the failed current source.

### PDF experience and downloads

Extend the M22 editor to a responsive file-tree/source/PDF layout. Reuse M15's
safe source-ID PDF behaviors where appropriate:

- an accessible in-app PDF preview with loading, empty, stale, and failure
  states;
- open in a separate window using safe opener behavior;
- `GET`/`HEAD` and byte-range support for the latest verified project PDF;
- private no-store caching and content-sniffing protection;
- a safely encoded project-derived filename;
- **Download latest PDF** on the project overview only when a successful PDF
  exists;
- existing `main.tex` and complete-source ZIP downloads alongside the PDF.

Only a validated project UUID and backend-derived expected build path may
resolve PDF content. Verify regular-file type, PDF signature, size, and hash
before streaming. Never expose compiler auxiliary files or a physical path.

### Work order

1. Add a pinned, reproducible TeX Live/latexmk compiler image with pdfLaTeX.
2. Add a dedicated offline, non-root, resource-bounded compiler worker and
   disposable job queue.
3. Add compile-job model, migration, schemas, repository, service, and
   worker adapter boundaries.
4. Snapshot only committed project source and compile from its root-relative
   main file.
5. Disable shell escape, custom configuration, runtime downloads, arbitrary
   commands, flags, and network access.
6. Add per-project 10–600-second timeout control with a separate hard ceiling.
7. Kill the complete process group on timeout and clean abandoned jobs.
8. Add bounded, sanitized, revision-aware compile logs and status polling.
9. Validate and atomically publish only successful PDFs while retaining the
   previous successful result after failure.
10. Add the responsive PDF preview, new-window action, and safe downloads.
11. Add mocked ordinary tests plus a real isolated compiler integration test.
12. Add escape, traversal, secret isolation, resource exhaustion, timeout,
    stale revision, PDF integrity, accessibility, and E2E tests.
13. Update setup, compiler-version, package-support, timeout, privacy,
    troubleshooting, backup, and recovery documentation.

## Completion criteria

- [ ] A saved multi-file project containing `main.tex`, an included chapter, a
  bibliography, and `images/diagram.png` compiles to a readable PDF using
  root-relative paths.
- [ ] The owner can change that project's timeout within the allowed range and
  the effective value is shown on each job.
- [ ] A deliberately long compile is terminated at the configured deadline,
  including child processes, and becomes `timed_out` without changing source.
- [ ] A LaTeX error becomes `failed` with a useful bounded root-relative log.
- [ ] Shell escape, custom compiler configuration, network access,
  parent/absolute reads, fork/process abuse, and oversized output fail inside
  the disposable sandbox without reaching application data.
- [ ] Successful PDFs can be previewed, opened separately, and downloaded from
  the editor and overview with safe range behavior.
- [ ] A later failure leaves the prior verified PDF available and clearly
  labelled as older; a stale-revision result is never presented as current.
- [ ] Compiler restarts and abandoned jobs resolve to safe terminal/expired
  states and disposable files are cleaned.
- [ ] Ordinary tests require neither a real Codex credential nor network access;
  one containerized test exercises the real compiler.
- [ ] Existing Documents source integrity and every earlier application module
  remain intact.
- [ ] Relevant tests, compiler integration, Docker startup, migrations, lint,
  production build, E2E, security checks, and `git diff --check` pass.

## Verification

This milestone adds a service, a migration, and Compose/configuration changes,
so verification covers Documents, the compiler worker, and the shared
deployment and recovery paths it touches.

- Focused Documents tests with the compiler mocked
  (`make test-module MODULE=documents`).
- One containerized integration test against the real isolated compiler.
- Security checks inside the sandbox: shell escape, custom configuration,
  network access, traversal and parent/absolute reads, secret isolation,
  fork/process abuse, resource exhaustion, and oversized output.
- Timeout, stale-revision, abandoned-job, and PDF-integrity cases.
- Browser and accessibility scenarios for preview and downloads (`make e2e`).
- `make test`, because the migration, shared configuration, and Compose files
  change.
- `make lint` and the frontend production build.
- Docker startup including the compiler worker, and migrations.
- Coordinated backup/restore with generated PDFs (`make data-relocation-test`).
- `git diff --check`.
