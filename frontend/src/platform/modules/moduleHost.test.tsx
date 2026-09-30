import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ModuleHost from "../../ModuleHost";
import { assembleModuleHostPages } from "./moduleHost";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("shared module host", () => {
  it("uses the real Documents entry while omitting unselected pages", () => {
    expect(
      assembleModuleHostPages("documents").map(({ id, moduleId }) => ({
        id,
        moduleId,
      })),
    ).toEqual([{ id: "documents", moduleId: "documents" }]);
  });

  it("uses the real Calendar entry while omitting unselected pages", () => {
    expect(
      assembleModuleHostPages("calendar").map(({ id, moduleId }) => ({
        id,
        moduleId,
      })),
    ).toEqual([{ id: "calendar", moduleId: "calendar" }]);
  });

  it.each(["", "unknown", "../documents", "calendar,documents"])(
    "rejects unsupported module id %j",
    (moduleId) => {
      expect(() => assembleModuleHostPages(moduleId)).toThrowError(
        "Unsupported module host",
      );
    },
  );

  it("renders Documents inside the real shell without unrelated navigation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Promise.resolve(
          new Response(JSON.stringify([]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        ),
      ),
    );

    render(<ModuleHost moduleId="documents" />);

    expect(screen.getByText("Teacher")).toBeInTheDocument();
    expect(screen.getByText("Assistant")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Documents" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.queryByRole("button", { name: "Calendar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Courses" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Inbox" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Assistant" })).toBeNull();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  });

  it("renders Calendar inside the real shell without unrelated navigation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Promise.resolve(
          new Response(JSON.stringify([]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        ),
      ),
    );

    render(<ModuleHost moduleId="calendar" />);

    expect(screen.getByRole("button", { name: "Calendar" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.queryByRole("button", { name: "Courses" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Documents" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Assistant" })).toBeNull();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  });
});
