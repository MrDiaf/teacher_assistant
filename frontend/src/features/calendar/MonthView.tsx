import type { CSSProperties } from "react";

import {
  dateKey,
  eventsForDay,
  formatEventTime,
  isSameDay,
  WEEKDAY_LABELS,
} from "./dateUtils";
import type { CalendarModel, DisplayCalendarEvent } from "./types";

interface MonthViewProps {
  anchor: Date;
  calendars: Map<string, CalendarModel>;
  days: Date[];
  events: DisplayCalendarEvent[];
  onCreate: (day: Date) => void;
  onMove: (event: DisplayCalendarEvent, day: Date) => void;
  onSelectEvent: (event: DisplayCalendarEvent) => void;
}

export function MonthView({
  anchor,
  calendars,
  days,
  events,
  onCreate,
  onMove,
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
              onDragOver={(dragEvent) => dragEvent.preventDefault()}
              onDrop={(dragEvent) => {
                const draggedId = dragEvent.dataTransfer.getData(
                  "text/calendar-event-id",
                );
                const dragged = events.find(
                  (candidate) => candidate.display_id === draggedId,
                );
                if (dragged) onMove(dragged, day);
              }}
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
                  const isReadOnly = calendar?.is_read_only ?? true;
                  const style = {
                    "--event-color": calendar?.color ?? "#29584c",
                  } as CSSProperties;
                  return (
                    <button
                      className={`month-event status-${event.status}${
                        event.all_day ? " all-day-event" : ""
                      }${isReadOnly ? " protected-event" : ""}`}
                      draggable={!isReadOnly}
                      key={event.display_id}
                      onClick={() => onSelectEvent(event)}
                      onDragStart={(dragEvent) => {
                        dragEvent.dataTransfer.effectAllowed = "move";
                        dragEvent.dataTransfer.setData(
                          "text/calendar-event-id",
                          event.display_id,
                        );
                      }}
                      style={style}
                      title={`${formatEventTime(event)} ${event.title}`}
                      type="button"
                    >
                      <span className="month-event-time">
                        {formatEventTime(event)}
                      </span>
                      <span>{event.title}</span>
                      {(event.series_id || event.recurrence_rule) && (
                        <span
                          aria-label="Recurring event"
                          className="recurrence-mark"
                        >
                          ↻
                        </span>
                      )}
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
