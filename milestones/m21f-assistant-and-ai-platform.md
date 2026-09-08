# M21F - Assistant boundary, shared AI runtime, and diagnostics

- [ ] This milestone

## Outcome

Separate Assistant's conversation/proposal workflow from reusable AI runtime
and diagnostic services, preserving the existing security and confirmation flow.

Dependency: [M21E](m21e-courses-module-boundary.md). Planning only. Do not add
new runtime actions, broader context access, or Documents compilation advice.

## Scope

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

## Ordered checklist

- [ ] Complete Assistant public entries and remove remaining foreign internals.
- [ ] Restructure shared AI/diagnostics behind the M21B platform interfaces.
- [ ] Add platform-owned AI settings access while preserving current sign-in.
- [ ] Separate Assistant UI/service orchestration, styles, and focused fixtures.
- [ ] Test real Calendar/Courses contracts with mocked Codex, including failure,
  cancellation, privacy, stale permissions, and repeated-confirmation paths.
- [ ] Update Assistant/platform README/handoffs and close boundary allowances.

## Acceptance criteria

- Assistant can mount in the shared host with contract-checked fake capabilities
  and with real selected providers; unavailable capabilities fail explicitly.
- Ordinary tests use no Codex credentials and no real model requests.
- Notes summaries/prettify work without loading Assistant feature internals;
  shared authentication and diagnostics remain available independently.
- Runtime jobs still receive no repository, shell, Docker socket, credentials,
  or unbounded filesystem/data access; cancellation/timeout deletes workspaces.
- Unknown actions, read-only mutations, bulk/delete-calendar requests, invalid
  references, and repeated confirmation retain their enforced behavior.
- Drafts survive navigation/failure as before; completed status follows actual
  backend execution and never a speculative model response.
- Focused/runtime/contract tests, cross-module E2E, accessibility, lint/build,
  Docker startup, migration compatibility, and diff checks pass.

## Expected implementation areas

Assistant frontend/backend/styles/tests, AI/runtime/diagnostic platform modules,
Settings contribution, public provider adapters, architecture rules, and local
documentation. Existing source template paths and runtime isolation remain valid.

Stop after verification. [M21G](m21g-inbox-and-settings-boundary.md) requires
explicit selection.
