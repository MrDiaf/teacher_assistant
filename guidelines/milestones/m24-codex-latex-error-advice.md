# M24 — Codex advice for LaTeX compilation errors

## Objective

After a failed or timed-out M23 compilation, let the owner ask Codex for a
bounded explanation and practical advice. Codex receives only the relevant
sanitized compilation context and never edits a document, executes a compiler,
or claims that a fix was applied.

## Dependencies

Requires M23 to be complete because advice is requested for a terminal
failed/timed-out compile job and its recorded source revision. M23/M22 retain
the prerequisite M21A-M21I refactoring gate. Reuse the shared AI platform
independently of whether the Assistant navigation module is enabled. Inspect
the resulting repository state first; read
[M23](m23-isolated-latex-compilation.md) only if additional intent is required.

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
Use Documents public registration, its own styles/tests, and the shared AI
contract; do not reintroduce direct shell wiring or dependency on Assistant
internals. Disabled Documents cannot admit advice jobs or expose its context.

```text
backend/app/documents/advice_schemas.py
backend/app/documents/advice_service.py
backend/app/documents/advice_routes.py
backend/app/documents/compilation_repository.py
backend/app/codex_runtime/workspace.py
backend/app/codex_runtime/workspace_template/LATEX_ADVICE_AGENT.md
Documents public module entry established during M21B-M21C
backend/app/core/errors.py
backend/tests/test_document_compile_advice.py
backend/tests/test_codex_runtime.py
frontend/src/features/documents/CompileAdvice.tsx
frontend/src/features/documents/DocumentEditor.tsx
frontend/src/features/documents/api.ts
frontend/src/features/documents/types.ts
frontend/src/features/documents/*.test.tsx
Documents-owned stylesheet established in M21C
e2e/tests/
README.md
backend/app/codex_runtime/README.md
handoff.md
```

Not authorized: advice is read-only. There is no Apply, automatic patch,
automatic save, automatic recompile, source mutation proposal, project
deletion, package installation, or shell-command action in this milestone.

Stop after verification. M24 completes only the approved Documents/LaTeX
roadmap. Do not infer a later automatic-fix, collaboration, history,
course-linking, or additional compiler milestone from its limitations.

## Required work

### Owner workflow

```text
Compilation fails or times out
    -> owner reviews the bounded compiler log
    -> presses Ask Codex about this error
    -> selects/uses an allowed model
    -> backend selects bounded relevant source excerpts
    -> private read-only Codex job returns validated advice
    -> owner reviews file/line references and suggested steps
    -> owner edits and saves source manually
    -> owner starts a new compilation explicitly
```

Advice is read-only. There is no Apply, automatic patch, automatic save,
automatic recompile, source mutation proposal, project deletion, package
installation, or shell-command action in this milestone.

### Dedicated service and runtime boundary

Add a dedicated document-compilation-advice route and application service.
Do not route this through calendar proposals, the general Assistant
conversation, the compiler worker, or the generic diagnostic record alone.

Reuse the existing server-authoritative AI model allowlist, Codex adapter,
authentication, isolated workspace conventions, safe timeout handling, and
mocking patterns. The browser never communicates directly with Codex.

For each request, the backend must:

1. Resolve the exact project and terminal failed/timed-out compile job.
2. Confirm that the job belongs to that project and record the source revision
   it compiled.
3. Sanitize temporary absolute paths and select only root-relative source
   locations that existed in that compiled revision.
4. Build a private temporary workspace containing only the bounded advice
   input and a strict output schema.
5. Run Codex with tools, network, shell, application access, repository access,
   and writes disabled.
6. Parse and validate the complete response before returning it.
7. Delete the workspace immediately whether the job succeeds, fails, times
   out, or is cancelled by the request lifecycle.

Do not send database credentials, `.env`, Docker data, Codex authentication,
other projects, current source from a different revision, images/binaries,
PDFs, course files, calendars, Inbox items, Assistant conversations, raw
application logs, or arbitrary host paths.

### Bounded untrusted context

The LaTeX source and compiler log are private, untrusted data and never runtime
instructions. A comment, macro, filename, bibliography entry, or log line that
says to ignore policy or call a tool has no authority.

Use explicit documented limits. The implementation should supply no more than:

- the selected engine, effective compile timeout, terminal status, and elapsed
  runtime;
- 60,000 sanitized log characters, with truncation identified;
- 500 root-relative file-tree entries without binary contents;
- the bounded main-document source plus excerpts around parsed error locations;
- at most 8 source files and 80,000 total source characters;
- line-numbered excerpts rather than unrelated complete project contents when
  sufficient.

If safe relevant context cannot be selected, return a clear explanation that
advice is unavailable rather than broadening access. The Codex runtime never
opens files independently; required context is embedded by backend code.

The compilation timeout from M23 controls only TeX. Codex advice continues to
use the separate configured AI timeout and may not raise or reuse the compiler
deadline.

### Strict advice response

Define a closed structured schema containing only bounded fields such as:

- a plain-language explanation;
- up to 5 likely causes;
- up to 8 suggested manual steps;
- optional root-relative source locations with existing file paths and valid
  line ranges;
- whether retrying without a source/configuration change is likely useful;
- a reminder that no source was changed.

The schema must not contain executable commands, replacement source bodies,
patches, arbitrary HTML, hidden reasoning, tool calls, or claims of successful
mutation. Render advice as inert React text and structured lists, never as
unsanitized HTML.

Backend validation must reject extra fields, invalid UTF-8, oversized values,
unknown paths, paths outside the compiled snapshot, impossible line ranges,
duplicate locations, unsupported status claims, and any response that says a
document was modified. Invalid output leaves every source file, compile job,
and latest successful PDF unchanged.

Validated advice is an ephemeral response in this milestone. Do not persist raw
model output, hidden reasoning, rejected output, or advice text in the database
or ordinary logs. The owner may request a fresh explanation later.

### UI behavior

- Show **Ask Codex about this error** only for eligible failed/timed-out jobs.
- Reuse the shared model selector rather than duplicating model IDs.
- Explain exactly what bounded private data will be sent.
- Show a working state and prevent duplicate requests.
- Preserve the compile log and source editor state through success or failure.
- Present explanation, causes, manual steps, and validated file/line references
  accessibly beside the compiler result.
- Let a referenced existing text file be opened at the approximate line without
  applying any edit.
- Clearly state that Codex supplied advice only and that the owner must edit,
  save, and compile again.
- Authentication, invalid-model, timeout, malformed-output, unavailable
  context, and network/runtime failures must be readable and retryable where
  safe.

Opening a referenced file is navigation, not confirmation of or agreement with
the suggestion.

### Work order

1. Define the bounded advice request/response schema and dedicated runtime
   policy.
2. Add deterministic failed-job and source-revision context selection.
3. Add compiler-log path sanitization and strict context-size limits.
4. Add a dedicated advice service and API route using the shared Codex
   adapter/model allowlist.
5. Add a private read-only workspace containing only embedded bounded
   context and delete it immediately.
6. Validate every model field, source path, line range, limit, and no-change
   claim.
7. Add the eligible error action, privacy explanation, working state, advice
   panel, and source-location navigation.
8. Ensure no Codex result can edit, save, delete, compile, install, or execute
   anything.
9. Add prompt-injection, privacy, fabricated-location, malformed-output,
   oversized-context, timeout, and cleanup tests with Codex mocked.
10. Add frontend interaction, keyboard, accessibility, and E2E tests.
11. Update runtime policy, privacy, troubleshooting, and owner workflow
    documentation.

## Completion criteria

- [ ] A known missing-file or LaTeX syntax error receives a readable
  explanation, bounded likely causes, and useful manual steps.
- [ ] Every returned file reference names an existing root-relative text file
  from the failed job's exact source revision and uses a valid line range.
- [ ] Source/log prompt injection cannot expand context, call tools, access the
  compiler, or weaken validation.
- [ ] Codex receives no images, PDF, other project, repository, credential,
  calendar, course, Inbox, or unrelated private content.
- [ ] Requesting, closing, rejecting, timing out, or failing advice leaves
  source, project metadata, compile history, and the latest PDF byte-for-byte
  unchanged.
- [ ] The UI never claims an error was fixed or a document recompiled.
- [ ] Invalid paths, invented lines, oversized output, extra fields, malformed
  JSON, unknown models, missing authentication, and runtime failures fail
  safely with no stored raw output.
- [ ] The temporary workspace is deleted on every terminal path.
- [ ] Ordinary tests use a mocked Codex adapter and require no real credentials.
- [ ] Existing Assistant, note Prettify, compiler isolation, Documents editing,
  and earlier module behavior remain intact.
- [ ] Relevant backend, runtime, frontend, privacy, accessibility, E2E, lint,
  production build, Docker, and `git diff --check` checks pass.

## Verification

This milestone stays inside Documents but consumes the shared AI runtime, so
verification covers Documents advice plus the runtime workspace tests and the
existing AI consumers (Assistant, note Prettify).

- Focused Documents backend and frontend tests with Codex mocked
  (`make test-module MODULE=documents`), including prompt-injection, privacy,
  fabricated-location, malformed-output, oversized-context, timeout, and
  workspace-cleanup cases.
- Codex runtime workspace tests, and the existing Assistant and note Prettify
  tests as affected consumers of the shared runtime.
- Interaction, keyboard, and accessibility browser scenarios (`make e2e`).
- `make lint` and the frontend production build.
- Docker startup.
- `git diff --check`.
