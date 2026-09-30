# M21F - Assistant boundary, shared AI runtime, and diagnostics

## Objective

Separate Assistant's conversation/proposal workflow from reusable AI runtime
and diagnostic services, preserving the existing security and confirmation flow.

## Dependencies

Requires M21E to be complete because Assistant consumes the real Courses public
contracts introduced there, alongside Calendar's public contracts from M21D.
Inspect the resulting repository state first; read
[M21E](m21e-courses-module-boundary.md) only if additional intent is required.

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

Authorized areas: Assistant frontend/backend/styles/tests, AI/runtime/diagnostic
platform modules, Settings contribution, public provider adapters, architecture
rules, and local documentation. Existing source template paths and runtime
isolation remain valid.

Not authorized:

- Do not add new runtime actions, broader context access, or Documents
  compilation advice.
- Do not create a universal AI prompt/workflow engine or give the platform
  permission to query every module's content.

Stop after verification. M21G requires explicit owner selection.

## Required work

Assistant owns conversations, messages, jobs, proposals, confirmation,
cancellation, progress, and its UI/drafts. It consumes the real Calendar and
Courses public contracts from M21D/M21E. Remove remaining direct imports of
their internals and any cyclic dependency through errors or diagnostics.

The platform owns reusable AI authentication, model allowlisting, Codex adapter,
private workspace lifecycle, and sanitized diagnostics. Maintain one runtime
implementation shared by Assistant and Courses. Authentication/model settings
must be accessible through a platform-owned Settings contribution without
requiring the Assistant feature to be enabled; preserve current Assistant
sign-in controls as delegates to that same service.

Feature services still select their bounded context, validate structured output,
and own job records. Do not create a universal AI prompt/workflow engine or give
the platform permission to query every module's content. Diagnostics accepts
bounded sanitized records through a public interface and does not depend on
Assistant conversation internals. Preserve the required runtime policy template
location and immediate workspace cleanup.

Split Assistant page/service orchestration along existing conversation,
proposal, progress, and error responsibilities. Keep module CSS scoped and
preserve original interaction/keyboard behavior and per-conversation drafts.
Retain permission rechecks, proposal expiry, linked-batch ordering, event limits,
idempotent confirmation, and transaction rollback through Calendar's contract.

### Work order

1. Complete Assistant public entries and remove remaining foreign internals.
2. Restructure shared AI/diagnostics behind the M21B platform interfaces.
3. Add platform-owned AI settings access while preserving current sign-in.
4. Separate Assistant UI/service orchestration, styles, and focused fixtures.
5. Test real Calendar/Courses contracts with mocked Codex, including failure,
   cancellation, privacy, stale permissions, and repeated-confirmation paths.
6. Update Assistant/platform README/handoffs, close boundary allowances, and
   update `PLAN.md`.

## Completion criteria

- [ ] Assistant can mount in the shared host with contract-checked fake
  capabilities and with real selected providers; unavailable capabilities fail
  explicitly.
- [ ] Ordinary tests use no Codex credentials and no real model requests.
- [ ] Notes summaries/prettify work without loading Assistant feature internals;
  shared authentication and diagnostics remain available independently.
- [ ] Runtime jobs still receive no repository, shell, Docker socket,
  credentials, or unbounded filesystem/data access; cancellation/timeout deletes
  workspaces.
- [ ] Unknown actions, read-only mutations, bulk/delete-calendar requests,
  invalid references, and repeated confirmation retain their enforced behavior.
- [ ] Drafts survive navigation/failure as before; completed status follows
  actual backend execution and never a speculative model response.
- [ ] Focused/runtime/contract tests, cross-module E2E, accessibility,
  lint/build, Docker startup, migration compatibility, and diff checks pass.

## Verification

This milestone changes the shared AI runtime and Assistant's consumer
contracts, so verification covers Assistant, the platform AI/diagnostics
modules, and the affected Calendar/Courses consumers.

- Focused Assistant, runtime, and contract tests with Codex mocked, including
  failure, cancellation, privacy, stale-permission, and repeated-confirmation
  paths.
- `make check-boundaries` with the Assistant allowances closed.
- Cross-module browser and accessibility scenarios (`make e2e`).
- `make test` as the affected-consumer gate for the shared runtime.
- `make lint` and the frontend production build.
- Docker startup and migration compatibility.
- `git diff --check`.
