import type { CSSProperties } from "react";
import { useEffect, useRef } from "react";

import {
  clampEventToDay,
  dateKey,
  eventsForDay,
  formatEventTime,
  HOUR_HEIGHT,
  isSameDay,
} from "./dateUtils";
import type { CalendarEvent, CalendarModel, CalendarView } from "./types";

interface TimeGridViewProps {
  calendars: Map<string, CalendarModel>;
  days: Date[];
  events: CalendarEvent[];
  onCreate: (day: Date) => void;
  onSelectEvent: (event: CalendarEvent) => void;
  view: Exclude<CalendarView, "month">;
}

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

export function TimeGridView({
  calendars,
  days,
  events,
  onCreate,
  onSelectEvent,
  view,
}: TimeGridViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const today = new Date();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = HOUR_HEIGHT * 7.5;
    }
  }, [view]);

  return (
    <section
      aria-label={`${view === "week" ? "Week" : "Day"} calendar`}
      className={`time-calendar ${view}-calendar`}
    >
      <div
        className="time-grid-header"
        style={{ "--day-count": days.length } as CSSProperties}
      >
        <div className="time-zone-label">Local</div>
        {days.map((day) => (
          <button
            className={
              isSameDay(day, today)
                ? "time-day-heading today"
                : "time-day-heading"
            }
            key={dateKey(day)}
            onClick={() => onCreate(day)}
            type="button"
          >
            <span>{day.toLocaleDateString("en", { weekday: "short" })}</span>
            <strong>{day.getDate()}</strong>
          </button>
        ))}
      </div>

      <div className="time-grid-scroll" ref={scrollRef}>
        <div
          className="time-grid-body"
          style={
            {
              "--day-count": days.length,
              "--hour-height": `${HOUR_HEIGHT}px`,
            } as CSSProperties
          }
        >
          <div className="time-gutter" aria-hidden="true">
            {HOURS.map((hour) => (
              <span key={hour}>{`${String(hour).padStart(2, "0")}:00`}</span>
            ))}
          </div>

          {days.map((day) => {
            const dayEvents = eventsForDay(events, day);
            const currentMinutes = today.getHours() * 60 + today.getMinutes();
            return (
              <div
                className={
                  isSameDay(day, today)
                    ? "time-day-column today"
                    : "time-day-column"
                }
                key={dateKey(day)}
              >
                {HOURS.map((hour) => {
                  const slotDate = new Date(day);
                  slotDate.setHours(hour, 0, 0, 0);
                  return (
                    <button
                      aria-label={`Create event on ${slotDate.toLocaleString(
                        "en",
                        {
                          month: "long",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        },
                      )}`}
                      className="hour-slot"
                      key={hour}
                      onClick={() => onCreate(slotDate)}
                      type="button"
                    />
                  );
                })}

                {isSameDay(day, today) && (
                  <div
                    className="current-time-line"
                    style={{ top: (currentMinutes / 60) * HOUR_HEIGHT }}
                  >
                    <span />
                  </div>
                )}

                {dayEvents.map((event) => {
                  const calendar = calendars.get(event.calendar_id);
                  const position = clampEventToDay(event, day);
                  const style = {
                    "--event-color": calendar?.color ?? "#29584c",
                    top: position.top,
                    height: position.height,
                  } as CSSProperties;
                  return (
                    <button
                      className={`time-event status-${event.status}`}
                      key={event.id}
                      onClick={() => onSelectEvent(event)}
                      style={style}
                      type="button"
                    >
                      <strong>{event.title}</strong>
                      <span>{formatEventTime(event)}</span>
                      {event.location && <small>{event.location}</small>}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
