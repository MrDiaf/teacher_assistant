# M25 — Isolated LaTeX compilation and PDF preview

- [ ] This milestone

## Outcome

Compile the saved main document with a mature LaTeX distribution, show a PDF
beside the source editor, and let the owner download the latest successful PDF
from either the editor or project overview. Compilation runs in a separately
isolated worker and has a per-project owner-adjustable timeout.

M24 must be complete first. Planning this milestone does not make it active.

## Compiler decision

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

## Compilation boundary

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

## Compiler sandbox

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

## Job and timeout model

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

## Logs and revision safety

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

## PDF experience and downloads

Extend the M24 editor to a responsive file-tree/source/PDF layout. Reuse M15's
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

## Milestone checklist

- [ ] Add a pinned, reproducible TeX Live/latexmk compiler image with pdfLaTeX.
- [ ] Add a dedicated offline, non-root, resource-bounded compiler worker and
  disposable job queue.
- [ ] Add compile-job model, migration, schemas, repository, service, and
  worker adapter boundaries.
- [ ] Snapshot only committed project source and compile from its root-relative
  main file.
- [ ] Disable shell escape, custom configuration, runtime downloads, arbitrary
  commands, flags, and network access.
- [ ] Add per-project 10–600-second timeout control with a separate hard ceiling.
- [ ] Kill the complete process group on timeout and clean abandoned jobs.
- [ ] Add bounded, sanitized, revision-aware compile logs and status polling.
- [ ] Validate and atomically publish only successful PDFs while retaining the
  previous successful result after failure.
- [ ] Add the responsive PDF preview, new-window action, and safe downloads.
- [ ] Add mocked ordinary tests plus a real isolated compiler integration test.
- [ ] Add escape, traversal, secret isolation, resource exhaustion, timeout,
  stale revision, PDF integrity, accessibility, and E2E tests.
- [ ] Update setup, compiler-version, package-support, timeout, privacy,
  troubleshooting, backup, and recovery documentation.

## Acceptance criteria

- A saved multi-file project containing `main.tex`, an included chapter, a
  bibliography, and `images/diagram.png` compiles to a readable PDF using
  root-relative paths.
- The owner can change that project's timeout within the allowed range and the
  effective value is shown on each job.
- A deliberately long compile is terminated at the configured deadline,
  including child processes, and becomes `timed_out` without changing source.
- A LaTeX error becomes `failed` with a useful bounded root-relative log.
- Shell escape, custom compiler configuration, network access, parent/absolute
  reads, fork/process abuse, and oversized output fail inside the disposable
  sandbox without reaching application data.
- Successful PDFs can be previewed, opened separately, and downloaded from the
  editor and overview with safe range behavior.
- A later failure leaves the prior verified PDF available and clearly labelled
  as older; a stale-revision result is never presented as current.
- Compiler restarts and abandoned jobs resolve to safe terminal/expired states
  and disposable files are cleaned.
- Ordinary tests require neither a real Codex credential nor network access;
  one containerized test exercises the real compiler.
- Existing Documents source integrity and every earlier application module
  remain intact.
- Relevant tests, compiler integration, Docker startup, migrations, lint,
  production build, E2E, security checks, and `git diff --check` pass.

## Expected implementation areas

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
frontend/src/styles.css
frontend tests and e2e/tests/
compose.yml, compose.dev.yml, and isolated test Compose files
Makefile
.env.example
README.md
docs/data-durability.md
handoff.md
```

Do not begin M26 until isolation, timeout enforcement, revision safety, and PDF
integrity are verified with the real compiler container.
