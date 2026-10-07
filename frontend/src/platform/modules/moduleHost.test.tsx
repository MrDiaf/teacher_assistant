import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ModuleHost from "../../ModuleHost";
import {
  assembleModuleHostPages,
  assembleModuleHostSettingsPanels,
} from "./moduleHost";

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

  it("uses the real Courses entry and hides its Calendar dependency page", () => {
    expect(
      assembleModuleHostPages("courses").map(({ id, moduleId }) => ({
        id,
        moduleId,
      })),
    ).toEqual([{ id: "courses", moduleId: "courses" }]);
  });

  it("uses the real Assistant entry and hides its provider pages", () => {
    expect(
      assembleModuleHostPages("assistant").map(({ id, moduleId }) => ({
        id,
        moduleId,
      })),
    ).toEqual([{ id: "assistant", moduleId: "assistant" }]);
  });

  it("uses the real Inbox page and Settings contribution", () => {
    expect(
      assembleModuleHostPages("inbox").map(({ id, moduleId }) => ({
        id,
        moduleId,
      })),
    ).toEqual([
      { id: "inbox", moduleId: "inbox" },
      { id: "settings", moduleId: "platform" },
    ]);
    expect(
      assembleModuleHostSettingsPanels("inbox").map(({ id, moduleId }) => ({
        id,
        moduleId,
      })),
    ).toEqual([{ id: "mail-inbox", moduleId: "inbox" }]);
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

  it("renders Courses inside the real shell without unrelated navigation", async () => {
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

    render(<ModuleHost moduleId="courses" />);

    expect(screen.getByRole("button", { name: "Courses" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.queryByRole("button", { name: "Calendar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Documents" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Inbox" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Assistant" })).toBeNull();
    expect(
      await screen.findByRole("heading", { name: "Create your first course" }),
    ).toBeInTheDocument();
  });

  it("renders Assistant with contract-shaped fake HTTP capabilities", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const url = String(input);
        const body = url.endsWith("/api/v1/ai/models")
          ? {
              default_model: "gpt-5.6-terra",
              models: [{ id: "gpt-5.6-terra", label: "GPT-5.6 Terra" }],
            }
          : url.endsWith("/api/v1/assistant/auth")
            ? {
                authenticated: false,
                auth_type: null,
                email: null,
                plan_type: null,
              }
            : [];
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );

    render(<ModuleHost moduleId="assistant" />);

    expect(screen.getByRole("button", { name: "Assistant" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.queryByRole("button", { name: "Calendar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Courses" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Documents" })).toBeNull();
    expect(
      await screen.findByRole("heading", {
        name: "Use your ChatGPT subscription",
      }),
    ).toBeInTheDocument();
  });

  it("renders Inbox and its mailbox panel through the shared focused host", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const url = String(input);
        const body = url.endsWith("/api/v1/ai/auth")
          ? {
              authenticated: false,
              auth_type: null,
              email: null,
              plan_type: null,
            }
          : url.endsWith("/api/v1/integrations/mail")
            ? {
                connected: false,
                status: null,
                host: null,
                port: null,
                tls_mode: null,
                mailbox: null,
                username: null,
                last_checked_at: null,
                last_success_at: null,
                next_check_at: null,
                safe_error_code: null,
                safe_error: null,
                source_warning: null,
                quarantined_count: 0,
              }
            : [];
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );

    render(<ModuleHost moduleId="inbox" />);
    expect(
      within(
        screen.getByRole("navigation", { name: "Main navigation" }),
      ).getByRole("button", { name: "Inbox" }),
    ).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("button", { name: "Calendar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Courses" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Documents" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Assistant" })).toBeNull();

    screen.getByRole("button", { name: "Settings" }).click();
    expect(
      await screen.findByRole("heading", { name: "Mail inbox" }),
    ).toBeInTheDocument();
  });
});
