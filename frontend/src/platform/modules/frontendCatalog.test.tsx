import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RegisteredApplication } from "../RegisteredApplication";
import { moduleCatalog } from "./catalog";
import { parseModuleCatalog } from "./contract";
import { registeredPages, registeredSettingsPanels } from "./frontendCatalog";
import {
  assembleFrontendPages,
  assembleFrontendSettingsPanels,
  type FrontendModuleEntry,
} from "./frontendContract";

describe("frontend module composition", () => {
  it("assembles every current page in stable navigation order", () => {
    expect(
      registeredPages.map(({ id, label, icon }) => ({ id, label, icon })),
    ).toEqual([
      { id: "dashboard", label: "Dashboard", icon: "dashboard" },
      { id: "calendar", label: "Calendar", icon: "calendar" },
      { id: "courses", label: "Courses", icon: "courses" },
      { id: "inbox", label: "Inbox", icon: "inbox" },
      { id: "documents", label: "Documents", icon: "file" },
      { id: "study-plan", label: "Study Plan", icon: "checklist" },
      { id: "assistant", label: "Assistant", icon: "assistant" },
      { id: "settings", label: "Settings", icon: "settings" },
    ]);
    expect(
      moduleCatalog.registrations.every(
        (registration) => registration.enabled_by_default,
      ),
    ).toBe(true);
  });

  it("mounts a test-only module without changing shell rendering", () => {
    function FixturePage() {
      return <main>Fixture module content</main>;
    }
    const fixtureCatalog = parseModuleCatalog({
      schema_version: 1,
      registrations: [
        {
          id: "fixture",
          display_name: "Fixture",
          order: 0,
          enabled_by_default: true,
          capabilities: ["page"],
          dependencies: [],
          contributions: {
            routes: [],
            pages: [{ id: "fixture-page", label: "Fixture", order: 0 }],
            settings_panels: [],
            lifecycle: [],
          },
        },
      ],
    });
    const fixtureEntry = {
      id: "fixture",
      pages: [{ id: "fixture-page", icon: "leaf", component: FixturePage }],
      settingsPanels: [],
    } as const satisfies FrontendModuleEntry<"fixture", "fixture-page">;
    const pages = assembleFrontendPages(fixtureCatalog, [fixtureEntry]);

    render(
      <RegisteredApplication
        activePage="fixture-page"
        onNavigate={vi.fn()}
        pages={pages}
        settingsPanels={[]}
      />,
    );

    expect(
      screen.getByRole("navigation", { name: "Main navigation" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fixture" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Fixture module content")).toBeInTheDocument();
  });

  it("rejects a module entry whose page code does not match metadata", () => {
    const mismatched = {
      id: "platform",
      pages: [],
      settingsPanels: [],
    } as const satisfies FrontendModuleEntry;

    expect(() =>
      assembleFrontendPages(moduleCatalog, [mismatched]),
    ).toThrowError("Missing frontend page code contribution");
  });

  it("rejects missing, unknown, and duplicate module code entries", () => {
    const fixtureCatalog = parseModuleCatalog({
      schema_version: 1,
      registrations: [
        {
          id: "fixture",
          display_name: "Fixture",
          order: 0,
          enabled_by_default: true,
          capabilities: [],
          dependencies: [],
          contributions: {
            routes: [],
            pages: [],
            settings_panels: [],
            lifecycle: [],
          },
        },
      ],
    });
    const fixtureEntry = {
      id: "fixture",
      pages: [],
      settingsPanels: [],
    } as const satisfies FrontendModuleEntry<"fixture", never>;

    expect(() => assembleFrontendPages(fixtureCatalog, [])).toThrowError(
      "Missing frontend module entry",
    );
    expect(() =>
      assembleFrontendPages(fixtureCatalog, [
        { id: "unknown", pages: [], settingsPanels: [] },
      ]),
    ).toThrowError("Unknown frontend module entry");
    expect(() =>
      assembleFrontendPages(fixtureCatalog, [fixtureEntry, fixtureEntry]),
    ).toThrowError("Duplicate frontend module entry");
  });

  it("rejects unknown and duplicate page code contributions", () => {
    function FixturePage() {
      return <main>Fixture</main>;
    }
    const fixtureCatalog = parseModuleCatalog({
      schema_version: 1,
      registrations: [
        {
          id: "fixture",
          display_name: "Fixture",
          order: 0,
          enabled_by_default: true,
          capabilities: ["page"],
          dependencies: [],
          contributions: {
            routes: [],
            pages: [{ id: "fixture-page", label: "Fixture", order: 0 }],
            settings_panels: [],
            lifecycle: [],
          },
        },
      ],
    });
    const page = {
      id: "fixture-page",
      icon: "leaf",
      component: FixturePage,
    } as const;

    expect(() =>
      assembleFrontendPages(fixtureCatalog, [
        {
          id: "fixture",
          pages: [{ ...page, id: "unknown-page" }],
          settingsPanels: [],
        },
      ]),
    ).toThrowError("Unknown frontend page code contribution");
    expect(() =>
      assembleFrontendPages(fixtureCatalog, [
        { id: "fixture", pages: [page, page], settingsPanels: [] },
      ]),
    ).toThrowError("Duplicate frontend page code contribution");
  });

  it("binds Inbox Settings metadata to its real module contribution", () => {
    expect(
      registeredSettingsPanels.map(({ id, label, moduleId }) => ({
        id,
        label,
        moduleId,
      })),
    ).toEqual([{ id: "mail-inbox", label: "Mail inbox", moduleId: "inbox" }]);
  });

  it("rejects missing, unknown, and duplicate Settings panel code", () => {
    function FixturePanel() {
      return <section>Fixture settings</section>;
    }
    const fixtureCatalog = parseModuleCatalog({
      schema_version: 1,
      registrations: [
        {
          id: "fixture",
          display_name: "Fixture",
          order: 0,
          enabled_by_default: true,
          capabilities: ["settings-panel"],
          dependencies: [],
          contributions: {
            routes: [],
            pages: [],
            settings_panels: [
              { id: "fixture-panel", label: "Fixture", order: 0 },
            ],
            lifecycle: [],
          },
        },
      ],
    });
    const panel = { id: "fixture-panel", component: FixturePanel } as const;

    expect(() =>
      assembleFrontendSettingsPanels(fixtureCatalog, [
        { id: "fixture", pages: [], settingsPanels: [] },
      ]),
    ).toThrowError("Missing frontend Settings panel code contribution");
    expect(() =>
      assembleFrontendSettingsPanels(fixtureCatalog, [
        {
          id: "fixture",
          pages: [],
          settingsPanels: [{ ...panel, id: "unknown-panel" }],
        },
      ]),
    ).toThrowError("Unknown frontend Settings panel code contribution");
    expect(() =>
      assembleFrontendSettingsPanels(fixtureCatalog, [
        { id: "fixture", pages: [], settingsPanels: [panel, panel] },
      ]),
    ).toThrowError("Duplicate frontend Settings panel code contribution");
  });
});
