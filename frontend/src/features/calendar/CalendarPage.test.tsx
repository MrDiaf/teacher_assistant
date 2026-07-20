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
  is_subscribed: false,
  subscription_last_synced_at: null,
  subscription_next_sync_at: null,
  subscription_error: null,
  created_at: now.toISOString(),
  updated_at: now.toISOString(),
};

const planningEvent: CalendarEvent = {
  id: "event-1",
  calendar_id: writableCalendar.id,
  title: "Planning session",
  description: "Prepare the week",
  location: "Home office",
  external_uid: null,
  start_at: eventStart.toISOString(),
  end_at: eventEnd.toISOString(),
  all_day: false,
  timezone: "Europe/Stockholm",
  recurrence_rule: null,
  recurrence_parent_id: null,
  recurrence_original_start_at: null,
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

      if (
        url.includes("/api/v1/calendar-imports/ics/preview?") &&
        method === "POST"
      ) {
        return jsonResponse({
          file_name: "schedule.ics",
          suggested_calendar_name: "School Schedule",
          total_events: 2,
          importable_events: 1,
          skipped_events: 1,
          events: [
            {
              index: 1,
              uid: "lesson-1@example.test",
              title: "Imported lesson",
              start_at: eventStart.toISOString(),
              end_at: eventEnd.toISOString(),
              all_day: false,
              timezone: "Europe/Stockholm",
              status: "confirmed",
              recurrence_rule: null,
              is_importable: true,
              issues: [],
            },
            {
              index: 2,
              uid: "unsupported@example.test",
              title: "Unsupported event",
              start_at: null,
              end_at: null,
              all_day: false,
              timezone: "Europe/Stockholm",
              status: "confirmed",
              recurrence_rule: null,
              is_importable: false,
              issues: [
                { severity: "error", message: "Missing required DTSTART." },
              ],
            },
          ],
        });
      }
      if (
        url.endsWith("/api/v1/calendar-subscriptions/ics/preview") &&
        method === "POST"
      ) {
        return jsonResponse({
          file_name: "Subscribed calendar.ics",
          suggested_calendar_name: "School Schedule",
          total_events: 1,
          importable_events: 1,
          skipped_events: 0,
          events: [
            {
              index: 1,
              uid: "lesson-1@example.test",
              title: "Subscribed lesson",
              start_at: eventStart.toISOString(),
              end_at: eventEnd.toISOString(),
              all_day: false,
              timezone: "Europe/Stockholm",
              status: "confirmed",
              recurrence_rule: null,
              is_importable: true,
              issues: [],
            },
          ],
        });
      }
      if (
        url.endsWith("/api/v1/calendar-subscriptions/ics") &&
        method === "POST"
      ) {
        const subscribedCalendar: CalendarModel = {
          ...writableCalendar,
          id: "calendar-subscribed",
          name: "School Schedule",
          is_read_only: true,
          source_type: "ics_import",
          is_subscribed: true,
          subscription_last_synced_at: now.toISOString(),
          subscription_next_sync_at: new Date(
            now.getTime() + 86_400_000,
          ).toISOString(),
        };
        const subscribedEvent: CalendarEvent = {
          ...planningEvent,
          id: "event-subscribed",
          calendar_id: subscribedCalendar.id,
          title: "Subscribed lesson",
          external_uid: "lesson-1@example.test",
        };
        calendar = subscribedCalendar;
        events = [subscribedEvent];
        return jsonResponse({
          calendar: subscribedCalendar,
          imported_count: 1,
          duplicate_count: 0,
          skipped_count: 0,
          errors: [],
          imported_events: [subscribedEvent],
          destination_calendar_id: subscribedCalendar.id,
        });
      }
      if (url.includes("/api/v1/calendar-imports/ics?") && method === "POST") {
        const importedCalendar: CalendarModel = {
          ...writableCalendar,
          id: "calendar-imported",
          name: "School Schedule",
          is_read_only: true,
          source_type: "ics_import",
        };
        const importedEvent: CalendarEvent = {
          ...planningEvent,
          id: "event-imported",
          calendar_id: importedCalendar.id,
          title: "Imported lesson",
          external_uid: "lesson-1@example.test",
        };
        calendar = importedCalendar;
        events = [importedEvent];
        return jsonResponse({
          calendar: importedCalendar,
          imported_count: 1,
          duplicate_count: 0,
          skipped_count: 1,
          errors: [
            {
              index: 2,
              uid: "unsupported@example.test",
              message: "Missing required DTSTART.",
            },
          ],
          imported_events: [importedEvent],
          destination_calendar_id: importedCalendar.id,
        });
      }

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
        const payload = JSON.parse(
          String(init?.body),
        ) as Partial<CalendarModel>;
        calendar = { ...calendar, ...payload };
        return jsonResponse(calendar);
      }
      if (url.endsWith("/api/v1/calendars") && method === "POST") {
        const payload = JSON.parse(
          String(init?.body),
        ) as Partial<CalendarModel>;
        calendar = {
          ...writableCalendar,
          ...payload,
          id:
            payload.name === writableCalendar.name
              ? writableCalendar.id
              : "calendar-created",
        };
        return jsonResponse(calendar, 201);
      }
      if (url.includes("/api/v1/calendars/") && method === "DELETE") {
        calendar = null;
        events = [];
        return new Response(null, { status: 204 });
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
      if (url.includes("/api/v1/events/") && method === "DELETE") {
        events = [];
        return new Response(null, { status: 204 });
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
    vi.restoreAllMocks();
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

    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(await screen.findByText("Office hours")).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).includes("/api/v1/events/event-created") &&
          init?.method === "PATCH" &&
          String(init.body).includes('"title":"Office hours"'),
      ),
    ).toBe(true);
  });

  it("closes dialogs with Escape and restores keyboard focus", async () => {
    render(<CalendarPage />);
    await screen.findByText("Planning session");
    const createButton = screen.getByRole("button", { name: "Create event" });

    createButton.focus();
    fireEvent.click(createButton);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveFocus();

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(createButton).toHaveFocus());
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

    const protectedEventText = await screen.findByText("Protected appointment");
    expect(protectedEventText.closest("button")).toHaveProperty(
      "draggable",
      false,
    );
    fireEvent.click(protectedEventText);
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
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    fireEvent.click(screen.getByRole("button", { name: "Week" }));
    await screen.findByLabelText("Week calendar");
    expect(document.querySelector(".event-resize-handle")).toBeNull();
  });

  it("creates and manages a local calendar", async () => {
    const fetchMock = installApiMock();
    render(<CalendarPage />);
    await screen.findByRole("checkbox", { name: "Show Personal" });

    fireEvent.click(screen.getByRole("button", { name: "Create calendar" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Name"), {
      target: { value: "Teaching" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Create calendar" }),
    );

    expect(
      await screen.findByRole("checkbox", { name: "Show Teaching" }),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/calendars",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"name":"Teaching"'),
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Manage Teaching" }));
    const manageDialog = screen.getByRole("dialog");
    fireEvent.change(within(manageDialog).getByLabelText("Description"), {
      target: { value: "Classes and office hours" },
    });
    fireEvent.click(
      within(manageDialog).getByRole("button", { name: "Save changes" }),
    );

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/calendars/calendar-created",
        expect.objectContaining({
          method: "PATCH",
          body: expect.stringContaining("Classes and office hours"),
        }),
      ),
    );
  });

  it("deletes a writable local calendar only after confirmation", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchMock = installApiMock({ initialEvents: [] });
    render(<CalendarPage />);
    await screen.findByRole("checkbox", { name: "Show Personal" });

    fireEvent.click(screen.getByRole("button", { name: "Manage Personal" }));
    fireEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Delete calendar",
      }),
    );

    expect(confirm).toHaveBeenCalledWith(
      expect.stringContaining("Delete “Personal” and all of its events?"),
    );
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/calendars/calendar-1",
        expect.objectContaining({ method: "DELETE" }),
      ),
    );
    expect(
      await screen.findByText("Set up your first calendar"),
    ).toBeInTheDocument();
  });

  it("creates an all-day recurring event", async () => {
    const fetchMock = installApiMock({ initialEvents: [] });
    render(<CalendarPage />);
    await screen.findByText("No events in this date range");

    fireEvent.click(screen.getByRole("button", { name: "Create event" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Title"), {
      target: { value: "School holiday" },
    });
    fireEvent.click(within(dialog).getByLabelText("All-day event"));
    fireEvent.change(within(dialog).getByLabelText("Repeats"), {
      target: { value: "weekly" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Create event" }),
    );

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).endsWith("/api/v1/events") && init?.method === "POST",
      );
      const payload = JSON.parse(String(call?.[1]?.body)) as CalendarEvent;
      expect(payload.all_day).toBe(true);
      expect(payload.recurrence_rule).toBe("FREQ=WEEKLY");
      expect(new Date(payload.end_at).getTime()).toBeGreaterThan(
        new Date(payload.start_at).getTime(),
      );
    });
  });

  it("searches event fields and sends calendar and date filters", async () => {
    const fetchMock = installApiMock();
    render(<CalendarPage />);
    await screen.findByText("Planning session");

    fireEvent.change(
      screen.getByPlaceholderText("Search title, description, or location"),
      { target: { value: "Home office" } },
    );
    fireEvent.change(screen.getByLabelText("Filter by calendar"), {
      target: { value: writableCalendar.id },
    });
    const dateText = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    fireEvent.change(screen.getByLabelText("Events from date"), {
      target: { value: dateText },
    });
    fireEvent.change(screen.getByLabelText("Events through date"), {
      target: { value: dateText },
    });

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) => {
          const requestUrl = String(url);
          return (
            requestUrl.includes("search=Home+office") &&
            requestUrl.includes(`calendar_id=${writableCalendar.id}`) &&
            requestUrl.includes("starts_before=") &&
            requestUrl.includes("ends_after=")
          );
        }),
      ).toBe(true),
    );
    expect(screen.getByText("1 event")).toBeInTheDocument();
  });

  it("moves and resizes writable timed events from the week grid", async () => {
    const fetchMock = installApiMock();
    render(<CalendarPage />);
    await screen.findByText("Planning session");
    fireEvent.click(screen.getByRole("button", { name: "Week" }));
    await screen.findByLabelText("Week calendar");

    const eventButton =
      document.querySelector<HTMLButtonElement>(".time-event")!;
    const targetSlot =
      document.querySelectorAll<HTMLButtonElement>(".hour-slot")[12];
    const values = new Map<string, string>();
    const dataTransfer = {
      effectAllowed: "none",
      getData: (type: string) => values.get(type) ?? "",
      setData: (type: string, value: string) => values.set(type, value),
    };
    fireEvent.dragStart(eventButton, { dataTransfer });
    fireEvent.drop(targetSlot, { dataTransfer });

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) =>
            String(url).includes("/api/v1/events/event-1") &&
            init?.method === "PATCH",
        ),
      ).toBe(true),
    );

    const resizeHandle = document.querySelector<HTMLElement>(
      ".event-resize-handle",
    );
    if (resizeHandle) {
      fireEvent.pointerDown(resizeHandle, { clientY: 100 });
      fireEvent.pointerUp(document, { clientY: 126 });
      await waitFor(() =>
        expect(
          fetchMock.mock.calls.filter(
            ([url, init]) =>
              String(url).includes("/api/v1/events/event-1") &&
              init?.method === "PATCH",
          ).length,
        ).toBeGreaterThanOrEqual(2),
      );
    }
  });

  it("edits one recurring occurrence without changing the series", async () => {
    const recurring = {
      ...planningEvent,
      id: "series-1",
      title: "Recurring planning",
      recurrence_rule: "FREQ=DAILY;COUNT=3",
    };
    const fetchMock = installApiMock({ initialEvents: [recurring] });
    render(<CalendarPage />);

    fireEvent.click((await screen.findAllByText("Recurring planning"))[0]);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("This occurrence")).toBeChecked();
    fireEvent.change(within(dialog).getByLabelText("Title"), {
      target: { value: "One changed occurrence" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Save changes" }),
    );

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) =>
            String(url).includes("recurrence_scope=occurrence") &&
            String(url).includes("occurrence_start_at=") &&
            init?.method === "PATCH",
        ),
      ).toBe(true),
    );
  });

  it("offers explicit complete-series editing", async () => {
    const recurring = {
      ...planningEvent,
      id: "series-1",
      title: "Recurring planning",
      recurrence_rule: "FREQ=WEEKLY;COUNT=3",
    };
    const fetchMock = installApiMock({ initialEvents: [recurring] });
    render(<CalendarPage />);

    fireEvent.click((await screen.findAllByText("Recurring planning"))[0]);
    const dialog = screen.getByRole("dialog");
    fireEvent.click(within(dialog).getByLabelText("Complete series"));
    expect(within(dialog).getByLabelText("Complete series")).toBeChecked();
    expect(within(dialog).getByLabelText("Repeats")).toHaveValue("weekly");
    fireEvent.change(within(dialog).getByLabelText("Title"), {
      target: { value: "Renamed complete series" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Save changes" }),
    );

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) =>
            String(url).includes(
              "/api/v1/events/series-1?recurrence_scope=series",
            ) && init?.method === "PATCH",
        ),
      ).toBe(true),
    );
  });

  it("previews an ICS file and imports valid events into a protected calendar", async () => {
    const fetchMock = installApiMock();
    render(<CalendarPage />);
    await screen.findByRole("checkbox", { name: "Show Personal" });

    fireEvent.click(
      screen.getByRole("button", { name: "Import or subscribe .ics" }),
    );
    const dialog = screen.getByRole("dialog");
    const file = new File(["BEGIN:VCALENDAR\nEND:VCALENDAR"], "schedule.ics", {
      type: "text/calendar",
    });
    fireEvent.change(within(dialog).getByLabelText("ICS file"), {
      target: { files: [file] },
    });

    expect(
      await within(dialog).findByText("Imported lesson"),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText("Missing required DTSTART."),
    ).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Import destination")).toHaveValue(
      "new",
    );
    expect(within(dialog).getByLabelText("Imported calendar name")).toHaveValue(
      "School Schedule",
    );

    fireEvent.click(
      within(dialog).getByRole("button", { name: "Import 1 event" }),
    );

    expect(
      await within(dialog).findByText("Import complete"),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/new imported calendar is read-only/i),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("checkbox", { name: "Show School Schedule" }),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).includes("/api/v1/calendar-imports/ics?") &&
          String(url).includes("calendar_name=School+Schedule") &&
          init?.method === "POST" &&
          init.body === file,
      ),
    ).toBe(true);
  });

  it("previews and creates a daily read-only ICS subscription", async () => {
    const fetchMock = installApiMock();
    render(<CalendarPage />);
    await screen.findByRole("checkbox", { name: "Show Personal" });

    fireEvent.click(
      screen.getByRole("button", { name: "Import or subscribe .ics" }),
    );
    const dialog = screen.getByRole("dialog");
    fireEvent.click(
      within(dialog).getByRole("tab", { name: "Subscribe by URL" }),
    );
    fireEvent.change(within(dialog).getByLabelText("ICS subscription URL"), {
      target: { value: "https://example.test/private.ics" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Preview subscription" }),
    );

    expect(
      await within(dialog).findByText("Subscribed lesson"),
    ).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Import destination")).toBeDisabled();
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Subscribe to 1 event" }),
    );

    expect(
      await within(dialog).findByText("Subscription added"),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/refreshes from its source daily/i),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith("/api/v1/calendar-subscriptions/ics") &&
          init?.method === "POST" &&
          String(init.body).includes("https://example.test/private.ics"),
      ),
    ).toBe(true);
  });
});
