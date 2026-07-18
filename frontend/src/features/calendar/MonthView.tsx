import type { CSSProperties } from "react";

import {
  dateKey,
  eventsForDay,
  formatEventTime,
  isSameDay,
  WEEKDAY_LABELS,
} from "./dateUtils";
import type { CalendarEvent, CalendarModel } from "./types";

interface MonthViewProps {
  anchor: Date;
  calendars: Map<string, CalendarModel>;
  days: Date[];
  events: CalendarEvent[];
  onCreate: (day: Date) => void;
  onSelectEvent: (event: CalendarEvent) => void;
}

export function MonthView({
  anchor,
  calendars,
  days,
  events,
  onCreate,
  onSelectEvent,
}: MonthViewProps) {
  const today = new Date();

  return (
    <section className="month-calendar" aria-label="Month calendar">
      <div className="month-weekdays" aria-hidden="true">
        {WEEKDAY_LABELS.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
      <div className="month-grid">
        {days.map((day) => {
          const dayEvents = eventsForDay(events, day);
          const outsideMonth = day.getMonth() !== anchor.getMonth();
          return (
            <div
              className={`month-cell${outsideMonth ? " outside-month" : ""}${
                isSameDay(day, today) ? " today" : ""
              }`}
              data-date={dateKey(day)}
              key={dateKey(day)}
            >
              <button
                aria-label={`Create event on ${day.toLocaleDateString("en", {
                  month: "long",
                  day: "numeric",
                })}`}
                className="month-day-number"
                onClick={() => onCreate(day)}
                type="button"
              >
                {day.getDate()}
              </button>
              <div className="month-events">
                {dayEvents.slice(0, 3).map((event) => {
                  const calendar = calendars.get(event.calendar_id);
                  const style = {
                    "--event-color": calendar?.color ?? "#29584c",
                  } as CSSProperties;
                  return (
                    <button
                      className={`month-event status-${event.status}`}
                      key={event.id}
                      onClick={() => onSelectEvent(event)}
                      style={style}
                      title={`${formatEventTime(event)} ${event.title}`}
                      type="button"
                    >
                      <span className="month-event-time">
                        {formatEventTime(event)}
                      </span>
                      <span>{event.title}</span>
                    </button>
                  );
                })}
                {dayEvents.length > 3 && (
                  <span className="more-events">
                    +{dayEvents.length - 3} more
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
