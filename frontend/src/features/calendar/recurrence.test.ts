import { describe, expect, it } from "vitest";

import { expandCalendarEvents } from "./recurrence";
import type { CalendarEvent } from "./types";

function event(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    id: "series-1",
    calendar_id: "calendar-1",
    title: "Weekly planning",
    description: null,
    location: null,
    external_uid: null,
    start_at: "2026-07-20T08:00:00.000Z",
    end_at: "2026-07-20T09:00:00.000Z",
    all_day: false,
    timezone: "Europe/Stockholm",
    recurrence_rule: "FREQ=WEEKLY;COUNT=4",
    recurrence_parent_id: null,
    recurrence_original_start_at: null,
    status: "confirmed",
    created_at: "2026-07-19T00:00:00.000Z",
    updated_at: "2026-07-19T00:00:00.000Z",
    ...overrides,
  };
}

describe("expandCalendarEvents", () => {
  it("expands a bounded recurring series inside the requested range", () => {
    const expanded = expandCalendarEvents(
      [event()],
      new Date("2026-07-19T00:00:00.000Z"),
      new Date("2026-08-20T00:00:00.000Z"),
    );

    expect(expanded).toHaveLength(4);
    expect(expanded.map((item) => item.start_at)).toEqual([
      "2026-07-20T08:00:00.000Z",
      "2026-07-27T08:00:00.000Z",
      "2026-08-03T08:00:00.000Z",
      "2026-08-10T08:00:00.000Z",
    ]);
    expect(expanded.every((item) => item.series_id === "series-1")).toBe(true);
  });

  it("replaces a generated occurrence with an exception and hides cancellations", () => {
    const moved = event({
      id: "exception-moved",
      title: "Moved planning",
      start_at: "2026-07-28T10:00:00.000Z",
      end_at: "2026-07-28T11:00:00.000Z",
      recurrence_rule: null,
      recurrence_parent_id: "series-1",
      recurrence_original_start_at: "2026-07-27T08:00:00.000Z",
    });
    const cancelled = event({
      id: "exception-cancelled",
      start_at: "2026-08-03T08:00:00.000Z",
      end_at: "2026-08-03T09:00:00.000Z",
      recurrence_rule: null,
      recurrence_parent_id: "series-1",
      recurrence_original_start_at: "2026-08-03T08:00:00.000Z",
      status: "cancelled",
    });

    const expanded = expandCalendarEvents(
      [event(), moved, cancelled],
      new Date("2026-07-19T00:00:00.000Z"),
      new Date("2026-08-20T00:00:00.000Z"),
    );

    expect(expanded.map((item) => item.title)).toEqual([
      "Weekly planning",
      "Moved planning",
      "Weekly planning",
    ]);
    expect(expanded.map((item) => item.start_at)).not.toContain(
      "2026-07-27T08:00:00.000Z",
    );
    expect(expanded.map((item) => item.start_at)).not.toContain(
      "2026-08-03T08:00:00.000Z",
    );
  });

  it("keeps all-day recurrence durations intact", () => {
    const expanded = expandCalendarEvents(
      [
        event({
          all_day: true,
          start_at: "2026-07-20T00:00:00.000Z",
          end_at: "2026-07-21T00:00:00.000Z",
          recurrence_rule: "FREQ=DAILY;COUNT=2",
        }),
      ],
      new Date("2026-07-20T00:00:00.000Z"),
      new Date("2026-07-23T00:00:00.000Z"),
    );

    expect(expanded.map((item) => [item.start_at, item.end_at])).toEqual([
      ["2026-07-20T00:00:00.000Z", "2026-07-21T00:00:00.000Z"],
      ["2026-07-21T00:00:00.000Z", "2026-07-22T00:00:00.000Z"],
    ]);
  });

  it("expands a weekly series across each selected BYDAY weekday", () => {
    const expanded = expandCalendarEvents(
      [
        event({
          start_at: "2026-07-22T17:00:00.000Z",
          end_at: "2026-07-22T19:00:00.000Z",
          recurrence_rule: "FREQ=WEEKLY;BYDAY=WE,SA;COUNT=5",
        }),
      ],
      new Date("2026-07-20T00:00:00.000Z"),
      new Date("2026-08-10T00:00:00.000Z"),
    );

    expect(expanded.map((item) => item.start_at)).toEqual([
      "2026-07-22T17:00:00.000Z",
      "2026-07-25T17:00:00.000Z",
      "2026-07-29T17:00:00.000Z",
      "2026-08-01T17:00:00.000Z",
      "2026-08-05T17:00:00.000Z",
    ]);
  });
});
