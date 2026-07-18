import type { CalendarEvent, DisplayCalendarEvent } from "./types";

interface ParsedRecurrence {
  frequency: "DAILY" | "WEEKLY" | "MONTHLY";
  interval: number;
  count: number | null;
  until: number | null;
}

function parseRecurrence(rule: string): ParsedRecurrence | null {
  const parts = new Map(
    rule.split(";").map((segment) => {
      const [key, value] = segment.split("=", 2);
      return [key, value];
    }),
  );
  const frequency = parts.get("FREQ");
  if (
    frequency !== "DAILY" &&
    frequency !== "WEEKLY" &&
    frequency !== "MONTHLY"
  ) {
    return null;
  }
  const interval = Number(parts.get("INTERVAL") ?? "1");
  const count = parts.has("COUNT") ? Number(parts.get("COUNT")) : null;
  const untilText = parts.get("UNTIL");
  const until = untilText
    ? Date.parse(
        untilText.replace(
          /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/,
          "$1-$2-$3T$4:$5:$6Z",
        ),
      )
    : null;
  if (
    !Number.isInteger(interval) ||
    interval < 1 ||
    (count !== null && (!Number.isInteger(count) || count < 1)) ||
    (until !== null && Number.isNaN(until))
  ) {
    return null;
  }
  return { frequency, interval, count, until };
}

function monthlyOccurrence(start: Date, index: number, interval: number) {
  const result = new Date(start);
  const day = start.getDate();
  result.setDate(1);
  result.setMonth(start.getMonth() + index * interval);
  const lastDay = new Date(
    result.getFullYear(),
    result.getMonth() + 1,
    0,
  ).getDate();
  result.setDate(Math.min(day, lastDay));
  return result;
}

function occurrenceAt(
  start: Date,
  recurrence: ParsedRecurrence,
  index: number,
) {
  if (recurrence.frequency === "MONTHLY") {
    return monthlyOccurrence(start, index, recurrence.interval);
  }
  const result = new Date(start);
  result.setDate(
    result.getDate() +
      index * recurrence.interval * (recurrence.frequency === "WEEKLY" ? 7 : 1),
  );
  return result;
}

function overlaps(event: CalendarEvent, rangeStart: Date, rangeEnd: Date) {
  return (
    new Date(event.start_at).getTime() < rangeEnd.getTime() &&
    new Date(event.end_at).getTime() > rangeStart.getTime()
  );
}

function displayEvent(
  event: CalendarEvent,
  options?: Partial<DisplayCalendarEvent>,
): DisplayCalendarEvent {
  return {
    ...event,
    display_id: event.id,
    occurrence_start_at: event.recurrence_original_start_at,
    series_id: event.recurrence_parent_id,
    is_virtual_occurrence: false,
    ...options,
  };
}

export function expandCalendarEvents(
  events: CalendarEvent[],
  rangeStart: Date,
  rangeEnd: Date,
): DisplayCalendarEvent[] {
  const exceptionsBySeries = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    if (event.recurrence_parent_id) {
      const current = exceptionsBySeries.get(event.recurrence_parent_id) ?? [];
      current.push(event);
      exceptionsBySeries.set(event.recurrence_parent_id, current);
    }
  }

  const expanded: DisplayCalendarEvent[] = [];
  const usedExceptionIds = new Set<string>();
  for (const event of events) {
    if (event.recurrence_parent_id) {
      continue;
    }
    if (!event.recurrence_rule) {
      if (overlaps(event, rangeStart, rangeEnd)) {
        expanded.push(displayEvent(event));
      }
      continue;
    }

    const recurrence = parseRecurrence(event.recurrence_rule);
    if (!recurrence) {
      if (overlaps(event, rangeStart, rangeEnd)) {
        expanded.push(displayEvent(event));
      }
      continue;
    }
    const seriesExceptions = exceptionsBySeries.get(event.id) ?? [];
    const exceptions = new Map(
      seriesExceptions
        .filter((item) => item.recurrence_original_start_at)
        .map((item) => [
          new Date(item.recurrence_original_start_at!).getTime(),
          item,
        ]),
    );
    const originalStart = new Date(event.start_at);
    const duration = new Date(event.end_at).getTime() - originalStart.getTime();

    for (let index = 0; index < 5000; index += 1) {
      if (recurrence.count !== null && index >= recurrence.count) {
        break;
      }
      const occurrenceStart = occurrenceAt(originalStart, recurrence, index);
      if (
        recurrence.until !== null &&
        occurrenceStart.getTime() > recurrence.until
      ) {
        break;
      }
      if (occurrenceStart.getTime() >= rangeEnd.getTime()) {
        break;
      }
      const occurrenceEnd = new Date(occurrenceStart.getTime() + duration);
      if (occurrenceEnd.getTime() <= rangeStart.getTime()) {
        continue;
      }
      const exception = exceptions.get(occurrenceStart.getTime());
      if (exception) {
        usedExceptionIds.add(exception.id);
        if (
          exception.status !== "cancelled" &&
          overlaps(exception, rangeStart, rangeEnd)
        ) {
          expanded.push(
            displayEvent(exception, {
              display_id: `${exception.id}:${occurrenceStart.toISOString()}`,
              occurrence_start_at: occurrenceStart.toISOString(),
              series_id: event.id,
            }),
          );
        }
        continue;
      }
      expanded.push(
        displayEvent(
          {
            ...event,
            start_at: occurrenceStart.toISOString(),
            end_at: occurrenceEnd.toISOString(),
          },
          {
            display_id: `${event.id}:${occurrenceStart.toISOString()}`,
            occurrence_start_at: occurrenceStart.toISOString(),
            series_id: event.id,
            is_virtual_occurrence: true,
          },
        ),
      );
    }

    for (const exception of seriesExceptions) {
      if (
        !usedExceptionIds.has(exception.id) &&
        exception.status !== "cancelled" &&
        overlaps(exception, rangeStart, rangeEnd)
      ) {
        expanded.push(
          displayEvent(exception, {
            display_id: `${exception.id}:${exception.recurrence_original_start_at}`,
            occurrence_start_at: exception.recurrence_original_start_at,
            series_id: event.id,
          }),
        );
      }
    }
  }

  return expanded.sort((first, second) =>
    first.start_at.localeCompare(second.start_at),
  );
}

export function recurrenceLabel(rule: string | null): string {
  if (!rule) return "Does not repeat";
  if (rule.includes("FREQ=DAILY")) return "Daily";
  if (rule.includes("FREQ=WEEKLY")) return "Weekly";
  if (rule.includes("FREQ=MONTHLY")) return "Monthly";
  return "Recurring";
}
