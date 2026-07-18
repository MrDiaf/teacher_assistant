import { describe, expect, it } from "vitest";

import {
  addDays,
  clampEventToDay,
  eventsForDay,
  getMonthDays,
  getViewRange,
  startOfWeek,
} from "./dateUtils";
import type { CalendarEvent } from "./types";

function eventBetween(start: Date, end: Date): CalendarEvent {
  return {
    id: "event-1",
    calendar_id: "calendar-1",
    title: "Planning session",
    description: null,
    location: null,
    start_at: start.toISOString(),
    end_at: end.toISOString(),
    all_day: false,
    timezone: "Europe/Stockholm",
    recurrence_rule: null,
    recurrence_parent_id: null,
    status: "confirmed",
    created_at: start.toISOString(),
    updated_at: start.toISOString(),
  };
}

describe("calendar date utilities", () => {
  it("starts weeks on Monday and builds a six-week month grid", () => {
    const anchor = new Date(2026, 6, 18, 12);
    const weekStart = startOfWeek(anchor);
    const monthDays = getMonthDays(anchor);

    expect(weekStart.getDay()).toBe(1);
    expect(monthDays).toHaveLength(42);
    expect(monthDays[0].getDay()).toBe(1);
    expect(monthDays.at(-1)?.getDay()).toBe(0);
  });

  it("returns an exclusive end date for every view range", () => {
    const anchor = new Date(2026, 6, 18, 12);
    const [weekStart, weekEnd] = getViewRange(anchor, "week");
    const [dayStart, dayEnd] = getViewRange(anchor, "day");

    expect(weekEnd).toEqual(addDays(weekStart, 7));
    expect(dayEnd).toEqual(addDays(dayStart, 1));
  });

  it("includes events that overlap a day and positions them in a time grid", () => {
    const day = new Date(2026, 6, 18);
    const event = eventBetween(
      new Date(2026, 6, 18, 10, 30),
      new Date(2026, 6, 18, 12),
    );

    expect(eventsForDay([event], day)).toEqual([event]);
    expect(clampEventToDay(event, day)).toEqual({ top: 546, height: 78 });
  });
});
