export type ModuleId =
  | "platform"
  | "calendar"
  | "courses"
  | "inbox"
  | "documents"
  | "assistant";

export type PageId =
  | "dashboard"
  | "calendar"
  | "courses"
  | "inbox"
  | "documents"
  | "study-plan"
  | "assistant"
  | "settings";

export interface OrderedContribution {
  readonly id: string;
  readonly label: string;
  readonly order: number;
}

export interface ModuleDependency {
  readonly id: string;
  readonly requires: readonly string[];
}

export interface ModuleContributions {
  readonly routes: readonly string[];
  readonly pages: readonly OrderedContribution[];
  readonly settings_panels: readonly OrderedContribution[];
  readonly lifecycle: readonly string[];
}

export interface ModuleRegistration {
  readonly id: string;
  readonly display_name: string;
  readonly order: number;
  readonly enabled_by_default: boolean;
  readonly capabilities: readonly string[];
  readonly dependencies: readonly ModuleDependency[];
  readonly contributions: ModuleContributions;
}

export interface ModuleCatalog {
  readonly registrations: readonly ModuleRegistration[];
  get(moduleId: string): ModuleRegistration | undefined;
}

export class ModuleContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ModuleContractError";
  }
}

const IDENTIFIER_PATTERN = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;

export function parseModuleCatalog(payload: unknown): ModuleCatalog {
  const catalog = objectWithKeys(payload, "catalog", [
    "schema_version",
    "registrations",
  ]);
  const schemaVersion = integer(
    catalog.schema_version,
    "catalog.schema_version",
  );
  if (schemaVersion !== 1) {
    throw new ModuleContractError("catalog.schema_version must be 1");
  }

  const registrations = array(
    catalog.registrations,
    "catalog.registrations",
  ).map(parseRegistration);
  validateRegistrations(registrations);
  const ordered = Object.freeze(
    [...registrations].sort((left, right) => left.order - right.order),
  );
  const byId = new Map(
    ordered.map((registration) => [registration.id, registration]),
  );

  return Object.freeze({
    registrations: ordered,
    get(moduleId: string) {
      return byId.get(moduleId);
    },
  });
}

function parseRegistration(value: unknown, index: number): ModuleRegistration {
  const path = `catalog.registrations[${index}]`;
  const raw = objectWithKeys(value, path, [
    "id",
    "display_name",
    "order",
    "enabled_by_default",
    "capabilities",
    "dependencies",
    "contributions",
  ]);
  const contributions = objectWithKeys(
    raw.contributions,
    `${path}.contributions`,
    ["routes", "pages", "settings_panels", "lifecycle"],
  );

  return Object.freeze({
    id: identifier(raw.id, `${path}.id`),
    display_name: nonEmptyString(raw.display_name, `${path}.display_name`),
    order: integer(raw.order, `${path}.order`),
    enabled_by_default: booleanValue(
      raw.enabled_by_default,
      `${path}.enabled_by_default`,
    ),
    capabilities: identifierArray(raw.capabilities, `${path}.capabilities`),
    dependencies: Object.freeze(
      array(raw.dependencies, `${path}.dependencies`).map(
        (dependency, dependencyIndex) =>
          parseDependency(
            dependency,
            `${path}.dependencies[${dependencyIndex}]`,
          ),
      ),
    ),
    contributions: Object.freeze({
      routes: identifierArray(
        contributions.routes,
        `${path}.contributions.routes`,
      ),
      pages: parseOrderedContributions(
        contributions.pages,
        `${path}.contributions.pages`,
      ),
      settings_panels: parseOrderedContributions(
        contributions.settings_panels,
        `${path}.contributions.settings_panels`,
      ),
      lifecycle: identifierArray(
        contributions.lifecycle,
        `${path}.contributions.lifecycle`,
      ),
    }),
  });
}

function parseDependency(value: unknown, path: string): ModuleDependency {
  const raw = objectWithKeys(value, path, ["id", "requires"]);
  return Object.freeze({
    id: identifier(raw.id, `${path}.id`),
    requires: identifierArray(raw.requires, `${path}.requires`),
  });
}

function parseOrderedContributions(
  value: unknown,
  path: string,
): readonly OrderedContribution[] {
  return Object.freeze(
    array(value, path).map((item, index) => {
      const itemPath = `${path}[${index}]`;
      const raw = objectWithKeys(item, itemPath, ["id", "label", "order"]);
      return Object.freeze({
        id: identifier(raw.id, `${itemPath}.id`),
        label: nonEmptyString(raw.label, `${itemPath}.label`),
        order: integer(raw.order, `${itemPath}.order`),
      });
    }),
  );
}

function validateRegistrations(
  registrations: readonly ModuleRegistration[],
): void {
  if (registrations.length === 0) {
    throw new ModuleContractError("catalog.registrations must not be empty");
  }

  requireUnique(
    registrations.map((registration) => registration.id),
    "duplicate module id",
  );
  requireUnique(
    registrations.map((registration) => registration.order),
    "duplicate module order",
  );
  const byId = new Map(
    registrations.map((registration) => [registration.id, registration]),
  );
  const contributionIds = {
    route: new Map<string, string>(),
    page: new Map<string, string>(),
    "settings panel": new Map<string, string>(),
    lifecycle: new Map<string, string>(),
  };
  const contributionOrders = {
    page: new Map<number, string>(),
    "settings panel": new Map<number, string>(),
  };

  for (const registration of registrations) {
    requireUnique(
      registration.dependencies.map((dependency) => dependency.id),
      `module ${JSON.stringify(registration.id)} declares a dependency twice`,
    );
    for (const dependency of registration.dependencies) {
      if (dependency.id === registration.id) {
        throw new ModuleContractError(
          `module ${JSON.stringify(registration.id)} cannot depend on itself`,
        );
      }
      const provider = byId.get(dependency.id);
      if (provider === undefined) {
        throw new ModuleContractError(
          `module ${JSON.stringify(registration.id)} requires unknown module ${JSON.stringify(dependency.id)}`,
        );
      }
      const missing = dependency.requires.filter(
        (capability) => !provider.capabilities.includes(capability),
      );
      if (missing.length > 0) {
        throw new ModuleContractError(
          `module ${JSON.stringify(registration.id)} requires capabilities not provided by ${JSON.stringify(dependency.id)}: ${missing.sort().join(", ")}`,
        );
      }
    }

    recordIds(
      registration.id,
      "route",
      registration.contributions.routes,
      contributionIds.route,
    );
    recordOrdered(
      registration.id,
      "page",
      registration.contributions.pages,
      contributionIds.page,
      contributionOrders.page,
    );
    recordOrdered(
      registration.id,
      "settings panel",
      registration.contributions.settings_panels,
      contributionIds["settings panel"],
      contributionOrders["settings panel"],
    );
    recordIds(
      registration.id,
      "lifecycle",
      registration.contributions.lifecycle,
      contributionIds.lifecycle,
    );
  }

  validateAcyclic(registrations, byId);
}

function recordIds(
  moduleId: string,
  kind: string,
  ids: readonly string[],
  existingIds: Map<string, string>,
): void {
  for (const id of ids) {
    const existingModule = existingIds.get(id);
    if (existingModule !== undefined) {
      throw new ModuleContractError(
        `duplicate ${kind} id ${JSON.stringify(id)} in modules ${JSON.stringify(existingModule)} and ${JSON.stringify(moduleId)}`,
      );
    }
    existingIds.set(id, moduleId);
  }
}

function recordOrdered(
  moduleId: string,
  kind: string,
  contributions: readonly OrderedContribution[],
  existingIds: Map<string, string>,
  existingOrders: Map<number, string>,
): void {
  recordIds(
    moduleId,
    kind,
    contributions.map((contribution) => contribution.id),
    existingIds,
  );
  for (const contribution of contributions) {
    const existingId = existingOrders.get(contribution.order);
    if (existingId !== undefined) {
      throw new ModuleContractError(
        `duplicate ${kind} order ${contribution.order}: ${JSON.stringify(existingId)} and ${JSON.stringify(contribution.id)}`,
      );
    }
    existingOrders.set(contribution.order, contribution.id);
  }
}

function validateAcyclic(
  registrations: readonly ModuleRegistration[],
  byId: ReadonlyMap<string, ModuleRegistration>,
): void {
  const visited = new Set<string>();
  const visiting: string[] = [];

  function visit(moduleId: string): void {
    if (visited.has(moduleId)) return;
    const cycleStart = visiting.indexOf(moduleId);
    if (cycleStart !== -1) {
      throw new ModuleContractError(
        `module dependency cycle: ${[...visiting.slice(cycleStart), moduleId].join(" -> ")}`,
      );
    }
    visiting.push(moduleId);
    for (const dependency of byId.get(moduleId)?.dependencies ?? []) {
      visit(dependency.id);
    }
    visiting.pop();
    visited.add(moduleId);
  }

  for (const registration of registrations) visit(registration.id);
}

function objectWithKeys(
  value: unknown,
  path: string,
  expectedKeys: readonly string[],
): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ModuleContractError(`${path} must be an object`);
  }
  const raw = value as Record<string, unknown>;
  const expected = new Set(expectedKeys);
  const actual = Object.keys(raw);
  const missing = expectedKeys.filter((key) => !(key in raw));
  const unknown = actual.filter((key) => !expected.has(key));
  if (missing.length > 0 || unknown.length > 0) {
    const details = [
      ...(missing.length > 0
        ? [`missing keys: ${missing.sort().join(", ")}`]
        : []),
      ...(unknown.length > 0
        ? [`unknown keys: ${unknown.sort().join(", ")}`]
        : []),
    ];
    throw new ModuleContractError(
      `${path} has invalid fields (${details.join("; ")})`,
    );
  }
  return raw;
}

function array(value: unknown, path: string): readonly unknown[] {
  if (!Array.isArray(value))
    throw new ModuleContractError(`${path} must be an array`);
  return value;
}

function nonEmptyString(value: unknown, path: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new ModuleContractError(`${path} must be a non-empty string`);
  }
  return value;
}

function identifier(value: unknown, path: string): string {
  const candidate = nonEmptyString(value, path);
  if (!IDENTIFIER_PATTERN.test(candidate)) {
    throw new ModuleContractError(
      `${path} must be a lowercase kebab-case identifier`,
    );
  }
  return candidate;
}

function integer(value: unknown, path: string): number {
  if (!Number.isInteger(value))
    throw new ModuleContractError(`${path} must be an integer`);
  return value as number;
}

function booleanValue(value: unknown, path: string): boolean {
  if (typeof value !== "boolean")
    throw new ModuleContractError(`${path} must be a boolean`);
  return value;
}

function identifierArray(value: unknown, path: string): readonly string[] {
  const identifiers = array(value, path).map((item, index) =>
    identifier(item, `${path}[${index}]`),
  );
  requireUnique(identifiers, `${path} contains duplicate identifier`);
  return Object.freeze(identifiers);
}

function requireUnique(
  values: readonly (string | number)[],
  message: string,
): void {
  const seen = new Set<string | number>();
  for (const value of values) {
    if (seen.has(value)) {
      throw new ModuleContractError(`${message}: ${JSON.stringify(value)}`);
    }
    seen.add(value);
  }
}
