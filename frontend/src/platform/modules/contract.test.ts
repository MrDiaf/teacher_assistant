import { describe, expect, it } from "vitest";

import catalogJson from "./catalog.json";
import { ModuleContractError, parseModuleCatalog } from "./contract";

type MutableCatalog = {
  schema_version: number;
  registrations: Array<Record<string, any>>;
};

function payload(): MutableCatalog {
  return structuredClone(catalogJson) as MutableCatalog;
}

describe("module registration contract", () => {
  it("preserves stable production module and page order", () => {
    const catalog = parseModuleCatalog(payload());

    expect(
      catalog.registrations.map((registration) => registration.id),
    ).toEqual([
      "platform",
      "calendar",
      "courses",
      "inbox",
      "documents",
      "assistant",
    ]);
    expect(
      [
        ...catalog.registrations.flatMap(
          (registration) => registration.contributions.pages,
        ),
      ]
        .sort((left, right) => left.order - right.order)
        .map((page) => page.id),
    ).toEqual([
      "dashboard",
      "calendar",
      "courses",
      "inbox",
      "documents",
      "study-plan",
      "assistant",
      "settings",
    ]);
    expect(catalog.get("calendar")?.display_name).toBe("Calendar");
    expect(catalog.get("browser-controlled-input")).toBeUndefined();
  });

  it.each([
    [
      "duplicate module IDs",
      (value: MutableCatalog) => {
        value.registrations[1].id = value.registrations[0].id;
      },
      "duplicate module id",
    ],
    [
      "duplicate module order",
      (value: MutableCatalog) => {
        value.registrations[1].order = value.registrations[0].order;
      },
      "duplicate module order",
    ],
    [
      "unknown dependencies",
      (value: MutableCatalog) => {
        value.registrations[1].dependencies[0].id = "missing-module";
      },
      "requires unknown module",
    ],
    [
      "duplicate dependency declarations",
      (value: MutableCatalog) => {
        value.registrations[1].dependencies.push(
          structuredClone(value.registrations[1].dependencies[0]),
        );
      },
      "declares a dependency twice",
    ],
    [
      "self dependencies",
      (value: MutableCatalog) => {
        value.registrations[0].dependencies.push({
          id: "platform",
          requires: ["shell"],
        });
      },
      "cannot depend on itself",
    ],
    [
      "missing provider capabilities",
      (value: MutableCatalog) => {
        value.registrations[1].dependencies[0].requires.push(
          "missing-capability",
        );
      },
      "requires capabilities not provided",
    ],
    [
      "dependency cycles",
      (value: MutableCatalog) => {
        value.registrations[0].dependencies.push({
          id: "assistant",
          requires: ["api"],
        });
      },
      "module dependency cycle",
    ],
    [
      "duplicate route IDs",
      (value: MutableCatalog) => {
        value.registrations[1].contributions.routes.push(
          value.registrations[0].contributions.routes[0],
        );
      },
      "duplicate route id",
    ],
    [
      "duplicate capabilities",
      (value: MutableCatalog) => {
        value.registrations[1].capabilities.push(
          value.registrations[1].capabilities[0],
        );
      },
      "contains duplicate identifier",
    ],
    [
      "duplicate page IDs",
      (value: MutableCatalog) => {
        value.registrations[1].contributions.pages.push(
          structuredClone(value.registrations[1].contributions.pages[0]),
        );
      },
      "duplicate page id",
    ],
    [
      "duplicate lifecycle IDs",
      (value: MutableCatalog) => {
        value.registrations[4].contributions.lifecycle.push(
          value.registrations[4].contributions.lifecycle[0],
        );
      },
      "contains duplicate identifier",
    ],
    [
      "duplicate page order",
      (value: MutableCatalog) => {
        value.registrations[1].contributions.pages[0].order =
          value.registrations[0].contributions.pages[0].order;
      },
      "duplicate page order",
    ],
    [
      "executable-looking fields",
      (value: MutableCatalog) => {
        value.registrations[1].import_path = "./calendar/entry";
      },
      "unknown keys: import_path",
    ],
  ])("rejects %s", (_name, mutate, expectedMessage) => {
    const value = payload();
    mutate(value);

    expect(() => parseModuleCatalog(value)).toThrowError(expectedMessage);
  });

  it("returns immutable parsed metadata detached from input", () => {
    const value = payload();
    const catalog = parseModuleCatalog(value);

    value.registrations[0].display_name = "Changed";

    expect(catalog.registrations[0].display_name).toBe("Platform");
    expect(() => {
      (catalog.registrations as Array<unknown>).push({});
    }).toThrow(TypeError);
  });

  it("uses the contract error type", () => {
    expect(() => parseModuleCatalog({})).toThrow(ModuleContractError);
  });
});
