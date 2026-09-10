import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RegisteredApplication } from "../RegisteredApplication";
import { moduleCatalog } from "./catalog";
import { parseModuleCatalog } from "./contract";
import { registeredPages } from "./frontendCatalog";
import {
  assembleFrontendPages,
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
    } as const satisfies FrontendModuleEntry<"fixture", "fixture-page">;
    const pages = assembleFrontendPages(fixtureCatalog, [fixtureEntry]);

    render(
      <RegisteredApplication
        activePage="fixture-page"
        onNavigate={vi.fn()}
        pages={pages}
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
    } as const satisfies FrontendModuleEntry;

    expect(() =>
      assembleFrontendPages(moduleCatalog, [mismatched]),
    ).toThrowError("Missing frontend page code contribution");
  });
});
