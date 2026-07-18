import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CalendarPage } from "./CalendarPage";
import type { CalendarEvent, CalendarModel } from "./types";

const now = new Date();
const eventStart = new Date(
  now.getFullYear(),
  now.getMonth(),
  now.getDate(),
  10,
);
const eventEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 11);

const writableCalendar: CalendarModel = {
  id: "calendar-1",
  name: "Personal",
  description: "My calendar",
  color: "#29584c",
  is_visible: true,
  is_read_only: false,
  source_type: "local",
  created_at: now.toISOString(),
  updated_at: now.toISOString(),
};

const planningEvent: CalendarEvent = {
  id: "event-1",
  calendar_id: writableCalendar.id,
  title: "Planning session",
  description: "Prepare the week",
  location: "Home office",
  start_at: eventStart.toISOString(),
  end_at: eventEnd.toISOString(),
  all_day: false,
  timezone: "Europe/Stockholm",
  recurrence_rule: null,
  recurrence_parent_id: null,
  status: "confirmed",
  created_at: now.toISOString(),
  updated_at: now.toISOString(),
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installApiMock(options?: {
  calendar?: CalendarModel;
  emptyCalendar?: boolean;
  initialEvents?: CalendarEvent[];
}) {
  let calendar: CalendarModel | null = options?.emptyCalendar
    ? null
    : (options?.calendar ?? writableCalendar);
  let events = options?.initialEvents ?? [planningEvent];
  const fetchMock = vi.fn(
    async (input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/v1/calendars") && method === "GET") {
        return jsonResponse(calendar ? [calendar] : []);
      }
      if (url.includes("/api/v1/events?") && method === "GET") {
        return jsonResponse(events);
      }
      if (
        calendar &&
        url.includes(`/api/v1/calendars/${calendar.id}`) &&
        method === "PATCH"
      ) {
        const payload = JSON.parse(String(init?.body)) as {
          is_visible: boolean;
        };
        calendar = { ...calendar, is_visible: payload.is_visible };
        return jsonResponse(calendar);
      }
      if (url.endsWith("/api/v1/calendars") && method === "POST") {
        calendar = writableCalendar;
        return jsonResponse(calendar, 201);
      }
      if (url.endsWith("/api/v1/events") && method === "POST") {
        const payload = JSON.parse(
          String(init?.body),
        ) as Partial<CalendarEvent>;
        const created = {
          ...planningEvent,
          ...payload,
          id: "event-created",
        } as CalendarEvent;
        events = [created];
        return jsonResponse(created, 201);
      }
      if (url.includes("/api/v1/events/") && method === "PATCH") {
        const payload = JSON.parse(
          String(init?.body),
        ) as Partial<CalendarEvent>;
        const updated = { ...events[0], ...payload };
        events = [updated];
        return jsonResponse(updated);
      }
      throw new Error(`Unexpected API request: ${method} ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("CalendarPage", () => {
  beforeEach(() => {
    installApiMock();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders events and switches between month, week, and day views", async () => {
    render(<CalendarPage />);

    expect(await screen.findByText("Planning session")).toBeInTheDocument();
    expect(screen.getByLabelText("Month calendar")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Week" }));
    expect(await screen.findByLabelText("Week calendar")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Day" }));
    expect(await screen.findByLabelText("Day calendar")).toBeInTheDocument();
  });

  it("sets up a first personal calendar from the empty state", async () => {
    installApiMock({ emptyCalendar: true, initialEvents: [] });
    render(<CalendarPage />);

    expect(
      await screen.findByText("Set up your first calendar"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Set up calendar" }));

    expect(
      await screen.findByRole("checkbox", { name: "Show Personal" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Month calendar")).toBeInTheDocument();
  });

  it("persists calendar visibility and removes hidden events from the grid", async () => {
    const fetchMock = installApiMock();
    render(<CalendarPage />);
    expect(await screen.findByText("Planning session")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "Show Personal" }));

    await waitFor(() =>
      expect(screen.queryByText("Planning session")).not.toBeInTheDocument(),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/calendars/${writableCalendar.id}`,
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ is_visible: false }),
      }),
    );
  });

  it("creates and edits an ordinary event", async () => {
    const fetchMock = installApiMock({ initialEvents: [] });
    render(<CalendarPage />);
    await screen.findByText("No events in this date range");

    fireEvent.click(screen.getByRole("button", { name: "Create event" }));
    const createDialog = screen.getByRole("dialog");
    fireEvent.change(within(createDialog).getByLabelText("Title"), {
      target: { value: "Office hours" },
    });
    fireEvent.click(
      within(createDialog).getByRole("button", { name: "Create event" }),
    );

    expect(await screen.findByText("Office hours")).toBeInTheDocument();
    const createCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        String(url).endsWith("/api/v1/events") && init?.method === "POST",
    );
    expect(createCall).toBeDefined();

    fireEvent.click(screen.getByText("Office hours"));
    const editDialog = screen.getByRole("dialog");
    const titleInput = within(editDialog).getByLabelText("Title");
    fireEvent.change(titleInput, { target: { value: "Updated office hours" } });
    fireEvent.click(
      within(editDialog).getByRole("button", { name: "Save changes" }),
    );

    expect(await screen.findByText("Updated office hours")).toBeInTheDocument();
  });

  it("shows read-only events without mutation controls", async () => {
    const protectedCalendar = {
      ...writableCalendar,
      id: "calendar-protected",
      name: "Imported timetable",
      is_read_only: true,
      source_type: "ics_import" as const,
    };
    const protectedEvent = {
      ...planningEvent,
      id: "event-protected",
      calendar_id: protectedCalendar.id,
      title: "Protected appointment",
    };
    installApiMock({
      calendar: protectedCalendar,
      initialEvents: [protectedEvent],
    });
    render(<CalendarPage />);

    fireEvent.click(await screen.findByText("Protected appointment"));
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByText(/belongs to a read-only calendar/),
    ).toBeInTheDocument();
    expect(
      within(dialog).queryByRole("button", { name: "Save changes" }),
    ).not.toBeInTheDocument();
    expect(
      within(dialog).queryByRole("button", { name: "Delete" }),
    ).not.toBeInTheDocument();
  });
});
