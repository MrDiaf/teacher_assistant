# M21B - Application composition and shared platform boundaries

- [ ] This milestone

## Outcome

Give the existing application one explicit assembly point for modules and a
small shared platform, preserving all current functionality and navigation.

Dependency: [M21A](m21a-module-ownership-and-baseline.md). Planning only; this
milestone does not activate itself or any subsequent migration.

## Scope

Introduce a typed, code-owned module catalog with stable IDs, navigation order,
public entry points, declared dependencies/capabilities, settings contributions,
and lifecycle registrations. Validate duplicate IDs/routes, unknown required
dependencies, and cycles. Browser input cannot name code to import or execute.

The frontend shell consumes registered page/settings contributions; the backend
application factory assembles public routers and startup/shutdown hooks. Keep
backend and frontend module identities in agreement with a tested manifest or
equivalent contract. All implemented modules remain enabled by default and
retain existing route URLs, response/error shapes, and browser-storage IDs.
The Settings module switches themselves belong to M21H.

Separate assembly from module internals in `App.tsx` and `app/main.py`. The
catalog is wiring, not a place for Calendar, mail, Course, or Assistant logic.
Use explicit imports and dependency injection rather than dynamic plugin
discovery or a global service locator. Module-selective test assembly must be
possible without starting unrelated schedulers or opening private storage.

Extract only shared shell styles, tokens, and existing common UI primitives.
Feature CSS moves with its owner in M21C-M21G; preserve cascade behavior during
the transition. Keep the original sidebar, mobile navigation, branding, focus
behavior, and placeholders. Avoid redesign or a new frontend framework.

Publish the existing shared AI/model-selection and diagnostic interfaces from
their present implementation locations so later modules can depend on a stable
platform contract. M21F owns their deeper restructuring. Move generic helpers
such as enum serialization out of Calendar internals as their consumers migrate.

Retain one PostgreSQL installation and centrally ordered Alembic history.
Module-local models remain registered for migrations regardless of test page
selection; selecting a page must not change the production schema. Existing
volumes, bind roots, backups, and credential exclusions stay compatible.

## Ordered checklist

- [ ] Implement and validate the common registration/dependency contract.
- [ ] Assemble frontend pages and backend routers through public entries.
- [ ] Register existing background lifecycle hooks with bounded shutdown and
  startup-failure cleanup; default full-app behavior remains unchanged.
- [ ] Establish shared UI/platform entry points and preserve navigation state.
- [ ] Add composition, missing-dependency, duplicate-registration, and lifecycle
  tests; tighten the corresponding M21A boundary allowances.
- [ ] Update platform README/handoff and root wiring documentation with actual
  extension points; record verification and the exact next step.

## Acceptance criteria

- Every current page mounts through the catalog in its original order, and
  previously stored module selections/drafts still restore correctly.
- A test-only fixture module can be registered and mounted without editing
  shell rendering logic or adding a production placeholder feature.
- Selected-module test assembly starts only explicitly selected runtime hooks;
  full application startup/shutdown still starts/stops existing jobs correctly.
- No business module imports shell assembly or unapproved platform internals.
- Backend/frontend identity drift and invalid dependency declarations fail tests.
- Relevant composition, persistence, API, accessibility/E2E, lint, production
  build, Docker startup, migration-head, and diff checks pass. Run full
  regression checks because this milestone changes application assembly.

## Expected implementation areas

Frontend app/shell/components/persistence, backend application factory and
public module entries, common configuration/errors/AI/diagnostic interfaces,
composition tests, architecture rules, and platform documentation. Avoid moving
every feature's implementation or introducing per-module production containers.

Stop after verification. [M21C](m21c-documents-module-pilot.md) requires explicit
selection.
