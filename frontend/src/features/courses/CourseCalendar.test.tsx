import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CalendarEvent, CalendarModel } from "../calendar/public";
import { CourseCalendar } from "./CourseCalendar";
import type { CourseModel } from "./types";

const now = new Date().toISOString();
const course: CourseModel = {
  id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  name: "Database Systems",
  course_code: "DAT101",
  description: "Relational data and query design",
  term: "Autumn 2026",
  color: "#29584c",
  status: "active",
  source_type: "manual",
  source_count: 0,
  calendar_count: 0,
  created_at: now,
  updated_at: now,
};

const writableCalendar: CalendarModel = {
  id: "calendar-writable",
  name: "Database lectures",
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
};

const readOnlyCalendar: CalendarModel = {
  ...writableCalendar,
  id: "calendar-read-only",
  name: "University timetable",
  color: "#5b7fa3",
  is_read_only: true,
  source_type: "ics_import",
};

function eventFor(calendar: CalendarModel, title: string): CalendarEvent {
  const start = new Date();
  start.setHours(10, 0, 0, 0);
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  return {
    id: `event-${calendar.id}`,
    calendar_id: calendar.id,
    title,
    description: null,
    location: null,
    external_uid: null,
    start_at: start.toISOString(),
    end_at: end.toISOString(),
    all_day: false,
    timezone: "Europe/Oslo",
    recurrence_rule: null,
    recurrence_parent_id: null,
    recurrence_original_start_at: null,
    status: "confirmed",
    created_at: now,
    updated_at: now,
  };
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installCalendarApi(initialLinkedIds: string[]) {
  let calendars = [writableCalendar, readOnlyCalendar].map((calendar) => ({
    ...calendar,
  }));
  let linkedIds = new Set(initialLinkedIds);
  const events = [
    eventFor(writableCalendar, "Linked database lecture"),
    eventFor(readOnlyCalendar, "Protected university lecture"),
  ];

  return vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = new URL(String(input), "http://teacher-assistant.test");
    const method = init?.method ?? "GET";

    if (url.pathname === "/api/v1/calendars" && method === "GET") {
      return jsonResponse(calendars);
    }
    if (
      url.pathname === `/api/v1/courses/${course.id}/calendars` &&
      method === "GET"
    ) {
      return jsonResponse(
        calendars.filter((calendar) => linkedIds.has(calendar.id)),
      );
    }
    if (
      url.pathname === `/api/v1/courses/${course.id}/calendars` &&
      method === "POST"
    ) {
      const payload = JSON.parse(String(init?.body)) as {
        calendar_id: string;
      };
      linkedIds.add(payload.calendar_id);
      return jsonResponse(
        calendars.find((calendar) => calendar.id === payload.calendar_id),
        201,
      );
    }
    if (
      url.pathname.startsWith(`/api/v1/courses/${course.id}/calendars/`) &&
      method === "DELETE"
    ) {
      linkedIds.delete(url.pathname.split("/").at(-1)!);
      return jsonResponse(undefined, 204);
    }
    if (
      url.pathname === `/api/v1/courses/${course.id}/events` &&
      method === "GET"
    ) {
      const selectedCalendar = url.searchParams.get("calendar_id");
      return jsonResponse(
        events.filter(
          (event) =>
            linkedIds.has(event.calendar_id) &&
            (!selectedCalendar || event.calendar_id === selectedCalendar),
        ),
      );
    }
    if (url.pathname.startsWith("/api/v1/calendars/") && method === "PATCH") {
      const calendarId = url.pathname.split("/").at(-1);
      const payload = JSON.parse(String(init?.body)) as {
        is_visible: boolean;
      };
      calendars = calendars.map((calendar) =>
        calendar.id === calendarId
          ? { ...calendar, is_visible: payload.is_visible }
          : calendar,
      );
      return jsonResponse(
        calendars.find((calendar) => calendar.id === calendarId),
      );
    }
    throw new Error(`Unhandled request: ${method} ${url.pathname}`);
  });
}

describe("CourseCalendar", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("links and unlinks an existing calendar without deleting its events", async () => {
    const fetchMock = installCalendarApi([]);
    const onCalendarCountChange = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <CourseCalendar
        course={course}
        onCalendarCountChange={onCalendarCountChange}
      />,
    );

    expect(
      await screen.findByRole("heading", {
        name: "No calendars linked yet",
      }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Calendar to link"), {
      target: { value: writableCalendar.id },
    });
    fireEvent.click(
      screen.getAllByRole("button", { name: "Link calendar" })[0],
    );

    expect(
      await screen.findByText("Linked database lecture"),
    ).toBeInTheDocument();
    expect(onCalendarCountChange).toHaveBeenLastCalledWith(1);

    fireEvent.click(
      screen.getByRole("button", {
        name: `Unlink ${writableCalendar.name}`,
      }),
    );
    await waitFor(() =>
      expect(
        screen.queryByText("Linked database lecture"),
      ).not.toBeInTheDocument(),
    );
    expect(
      await screen.findByRole("heading", {
        name: "No calendars linked yet",
      }),
    ).toBeInTheDocument();
    expect(onCalendarCountChange).toHaveBeenLastCalledWith(0);
    expect(
      fetchMock.mock.calls.filter(([input, init]) => {
        const url = new URL(String(input), "http://teacher-assistant.test");
        return (
          url.pathname === `/api/v1/courses/${course.id}/calendars` &&
          (init?.method ?? "GET") === "GET"
        );
      }),
    ).toHaveLength(3);
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) =>
          String(input).includes("/api/v1/events/") &&
          init?.method === "DELETE",
      ),
    ).toBe(false);
  });

  it("shows linked read-only events but disables every mutation control", async () => {
    const fetchMock = installCalendarApi([readOnlyCalendar.id]);
    vi.stubGlobal("fetch", fetchMock);

    render(
      <CourseCalendar
        course={{ ...course, calendar_count: 1 }}
        onCalendarCountChange={vi.fn()}
      />,
    );

    const event = await screen.findByText("Protected university lecture");
    expect(screen.getByRole("button", { name: "Create event" })).toBeDisabled();

    fireEvent.click(event);
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByText(/belongs to a read-only calendar/),
    ).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Title")).toBeDisabled();
    expect(
      within(dialog).queryByRole("button", { name: "Save changes" }),
    ).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    fireEvent.click(
      screen.getByRole("checkbox", {
        name: `Show ${readOnlyCalendar.name}`,
      }),
    );
    await waitFor(() =>
      expect(
        screen.queryByText("Protected university lecture"),
      ).not.toBeInTheDocument(),
    );
    expect(
      screen.getByText(/Visibility is shared with Calendar/),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) =>
          String(input).endsWith(`/api/v1/calendars/${readOnlyCalendar.id}`) &&
          init?.method === "PATCH",
      ),
    ).toBe(true);
  });

  it("restores a course-scoped Calendar view and anchor after remount", async () => {
    const fetchMock = installCalendarApi([writableCalendar.id]);
    vi.stubGlobal("fetch", fetchMock);

    const firstRender = render(
      <CourseCalendar
        course={{ ...course, calendar_count: 1 }}
        onCalendarCountChange={vi.fn()}
      />,
    );
    await screen.findByText("Linked database lecture");
    fireEvent.click(screen.getByRole("button", { name: "Day" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Previous date range" }),
    );
    const rememberedHeading = screen.getByRole("heading", {
      level: 1,
    }).textContent;

    firstRender.unmount();
    render(
      <CourseCalendar
        course={{ ...course, calendar_count: 1 }}
        onCalendarCountChange={vi.fn()}
      />,
    );

    expect(
      await screen.findByRole("button", { name: "Day", pressed: true }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      rememberedHeading ?? "",
    );
  });
});
