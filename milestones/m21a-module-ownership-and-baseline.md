# M21A - Module ownership, contracts, and refactoring baseline

- [ ] This milestone

## Outcome

Establish a concrete ownership map, enforceable dependency rules, concise module
documentation, and measured verification baseline before moving implementation.
This is the first of nine refactoring milestones inserted between M21 and M22.
Existing milestone IDs and completed acceptance criteria remain unchanged.

Dependency: [M21](m21-durable-documents-foundation.md). Planning only; the owner
must explicitly select this milestone before implementation starts.

## Scope and decisions

Adopt the modular-monolith target in [instructions.md](../instructions.md).
Inventory the actual frontend, backend, tests, scripts, migrations, and private
storage. Assign every area to the shell/platform or one feature owner:

- Calendar: calendars, events, recurrence, ICS, and subscriptions.
- Courses: course records, materials, notes, summaries, prettify, and ownership
  of course-calendar associations; the integration uses Calendar's public API.
- Assistant: conversations, context selection, proposals, and confirmation.
- Inbox: mail connection, synchronization, credentials, messages, attachments,
  and its contributed mailbox settings panel.
- Documents: the implemented M21 project/source foundation only.
- Platform: shell/navigation, Settings host, common UI primitives, configuration,
  database sessions, migration/backup coordination, AI runtime and diagnostics.
  Dashboard and Study Plan remain shell-owned placeholders.

Document the small public interface each consumer actually needs, including
input/output data, errors, permission enforcement, and transaction ownership.
Use typed in-process interfaces; do not add internal HTTP services or an event
bus. Record existing cross-module ORM imports, queries, foreign keys, CSS
dependencies, lifecycle hooks, and test-fixture coupling. Distinguish database
integrity references from business access to another module's tables.

Public contracts must not expose ORM entities, repositories, credentials,
physical storage paths, or unrestricted query/session objects. Define an
explicit application coordinator for genuinely atomic cross-module operations.
Keep migrations centrally ordered and existing foreign-key protection intact.

## Documentation and measurements

Create `docs/modules/README.md` as the ownership/dependency index and
`docs/modules/<owner>/README.md` plus `handoff.md` for each owner above. The
README owns scope, public contracts, file locations, and actual development/test
commands; the local handoff owns current work, verification, and the next step.
Link completed milestone evidence instead of copying it into every handoff.
Keep root handoff focused on application state, shared cautions, and active work.
Update the reading workflow so ordinary sessions read common rules, the chosen
milestone/module, and required dependency contracts, not all module histories.

Record reproducible full-suite and representative Documents-focused timings,
separating build/setup from execution and cold from warm runs. Use synthetic
fixtures and record commands, revision, environment, and failures. Include the
existing full test, E2E, lint/build, startup, and recovery baseline; report known
failures honestly rather than weakening assertions to obtain a clean baseline.

## Ordered checklist

- [ ] Map ownership, dependencies, data, public contracts, and transaction rules.
- [ ] Create concise module documentation and reduce duplicated root history.
- [ ] Add automated frontend/backend import-boundary checks using established
  tooling; record exact existing violations with an owning M21B-M21G removal
  milestone. Reject new violations and new dependency cycles without broad ignores.
- [ ] Verify the checks reject a deliberately invalid import in a test fixture.
- [ ] Record the functional and timing baseline with isolated synthetic data.
- [ ] Update the status index and handoff with verified results and next step.

## Acceptance criteria

- Every current implementation area has an owner and every cross-module
  dependency has a documented purpose and migration destination.
- Existing violations are enumerated; newly introduced forbidden imports fail.
- Module documents describe current code accurately without claiming isolation
  or commands that have not yet been implemented.
- Reproducible verification evidence is sufficient for the Documents pilot
  and final M21I comparison; no private content or runtime credentials are kept.
- No feature behavior, schema, storage identity, or visible design is changed.

## Expected implementation areas

`docs/modules/`, architecture-check configuration/tests, root Makefile check
entry point, `AGENTS.md`, `instructions.md`, and `handoff.md`. Source moves and
new module functionality are outside this milestone.

Stop after verification. [M21B](m21b-application-composition.md) requires its
own explicit selection.
