import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function response(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("App persisted navigation", () => {
  it("restores the active module and Calendar view/anchor while reloading API data", async () => {
    const now = new Date().toISOString();
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        if (url.endsWith("/api/v1/calendars") && method === "GET") {
          return response([
            {
              id: "calendar-1",
              name: "Personal",
              description: null,
              color: "#29584c",
              is_visible: true,
              is_read_only: false,
              source_type: "local",
              is_subscribed: false,
              subscription_last_synced_at: null,
              subscription_next_sync_at: null,
              subscription_error: null,
              created_at: now,
              updated_at: now,
            },
          ]);
        }
        if (url.includes("/api/v1/events?") && method === "GET") {
          return response([]);
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    const firstRender = render(<App />);
    expect(
      await screen.findByRole("button", { name: "Day", pressed: false }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Day" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Previous date range" }),
    );
    const rememberedHeading = screen.getByRole("heading", {
      level: 1,
    }).textContent;

    fireEvent.click(screen.getByRole("button", { name: "Dashboard" }));
    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Calendar" }));
    expect(
      await screen.findByRole("button", { name: "Day", pressed: true }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      rememberedHeading ?? "",
    );
    const calendarLoadCount = () =>
      fetchMock.mock.calls.filter(
        ([url, init]) =>
          String(url).endsWith("/api/v1/calendars") &&
          (init?.method ?? "GET") === "GET",
      ).length;
    await waitFor(() => expect(calendarLoadCount()).toBeGreaterThanOrEqual(4));
    const loadsBeforeReload = calendarLoadCount();

    firstRender.unmount();
    render(<App />);

    expect(
      await screen.findByRole("button", { name: "Day", pressed: true }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      rememberedHeading ?? "",
    );
    await waitFor(() =>
      expect(calendarLoadCount()).toBe(loadsBeforeReload + 1),
    );

    fireEvent.click(screen.getByRole("button", { name: "Today" }));
    expect(screen.getByRole("heading", { level: 1 })).not.toHaveTextContent(
      rememberedHeading ?? "",
    );
  });
});
