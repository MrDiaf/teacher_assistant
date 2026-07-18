import type { CalendarEvent, CalendarView } from "./types";

export const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const HOUR_HEIGHT = 52;

export function startOfDay(date: Date): Date {
  const result = new Date(date);
  result.setHours(0, 0, 0, 0);
  return result;
}

export function addDays(date: Date, count: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + count);
  return result;
}

export function startOfWeek(date: Date): Date {
  const result = startOfDay(date);
  const day = result.getDay();
  result.setDate(result.getDate() - ((day + 6) % 7));
  return result;
}

export function startOfMonth(date: Date): Date {
  const result = startOfDay(date);
  result.setDate(1);
  return result;
}

export function addMonths(date: Date, count: number): Date {
  const result = startOfMonth(date);
  result.setMonth(result.getMonth() + count);
  return result;
}

export function getMonthDays(anchor: Date): Date[] {
  const gridStart = startOfWeek(startOfMonth(anchor));
  return Array.from({ length: 42 }, (_, index) => addDays(gridStart, index));
}

export function getViewDays(anchor: Date, view: CalendarView): Date[] {
  if (view === "month") {
    return getMonthDays(anchor);
  }
  if (view === "week") {
    const weekStart = startOfWeek(anchor);
    return Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
  }
  return [startOfDay(anchor)];
}

export function getViewRange(anchor: Date, view: CalendarView): [Date, Date] {
  const days = getViewDays(anchor, view);
  return [startOfDay(days[0]), addDays(startOfDay(days.at(-1)!), 1)];
}

export function moveAnchor(
  anchor: Date,
  view: CalendarView,
  direction: -1 | 1,
): Date {
  if (view === "month") {
    return addMonths(anchor, direction);
  }
  return addDays(anchor, view === "week" ? direction * 7 : direction);
}

export function isSameDay(first: Date, second: Date): boolean {
  return (
    first.getFullYear() === second.getFullYear() &&
    first.getMonth() === second.getMonth() &&
    first.getDate() === second.getDate()
  );
}

export function dateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function eventsForDay<EventType extends CalendarEvent>(
  events: EventType[],
  day: Date,
): EventType[] {
  const dayStart = startOfDay(day).getTime();
  const dayEnd = addDays(startOfDay(day), 1).getTime();
  return events
    .filter((event) => {
      const eventStart = new Date(event.start_at).getTime();
      const eventEnd = new Date(event.end_at).getTime();
      return eventStart < dayEnd && eventEnd > dayStart;
    })
    .sort((first, second) => first.start_at.localeCompare(second.start_at));
}

export function formatHeading(anchor: Date, view: CalendarView): string {
  if (view === "month") {
    return new Intl.DateTimeFormat("en", {
      month: "long",
      year: "numeric",
    }).format(anchor);
  }
  if (view === "day") {
    return new Intl.DateTimeFormat("en", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(anchor);
  }

  const start = startOfWeek(anchor);
  const end = addDays(start, 6);
  const startText = new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
  }).format(start);
  const endText = new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(end);
  return `${startText} – ${endText}`;
}

export function formatEventTime(event: CalendarEvent): string {
  if (event.all_day) {
    return "All day";
  }
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(event.start_at));
}

export function toDateTimeLocal(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function defaultEventWindow(day: Date): [Date, Date] {
  const now = new Date();
  const start = new Date(day);
  const hasSelectedTime = start.getHours() !== 0 || start.getMinutes() !== 0;
  if (hasSelectedTime) {
    start.setSeconds(0, 0);
  } else if (isSameDay(day, now)) {
    start.setHours(now.getHours() + 1, 0, 0, 0);
  } else {
    start.setHours(9, 0, 0, 0);
  }
  const end = new Date(start);
  end.setHours(end.getHours() + 1);
  return [start, end];
}

export function clampEventToDay(
  event: CalendarEvent,
  day: Date,
): { top: number; height: number } {
  const dayStart = startOfDay(day).getTime();
  const dayEnd = addDays(startOfDay(day), 1).getTime();
  const start = Math.max(new Date(event.start_at).getTime(), dayStart);
  const end = Math.min(new Date(event.end_at).getTime(), dayEnd);
  const minutesFromStart = (start - dayStart) / 60_000;
  const durationMinutes = Math.max(0, (end - start) / 60_000);
  return {
    top: (minutesFromStart / 60) * HOUR_HEIGHT,
    height: Math.max(28, (durationMinutes / 60) * HOUR_HEIGHT),
  };
}
