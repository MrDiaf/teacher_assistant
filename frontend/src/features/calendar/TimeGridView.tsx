import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";
import { useEffect, useRef } from "react";

import {
  clampEventToDay,
  dateKey,
  eventsForDay,
  formatEventTime,
  HOUR_HEIGHT,
  isSameDay,
} from "./dateUtils";
import type {
  CalendarModel,
  CalendarView,
  DisplayCalendarEvent,
} from "./types";

interface TimeGridViewProps {
  calendars: Map<string, CalendarModel>;
  days: Date[];
  events: DisplayCalendarEvent[];
  onCreate: (day: Date) => void;
  onMove: (
    event: DisplayCalendarEvent,
    target: Date,
    useTargetTime: boolean,
  ) => void;
  onResize: (event: DisplayCalendarEvent, endAt: Date) => void;
  onSelectEvent: (event: DisplayCalendarEvent) => void;
  view: Exclude<CalendarView, "month">;
}

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

export function TimeGridView({
  calendars,
  days,
  events,
  onCreate,
  onMove,
  onResize,
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

  function draggedEvent(dataTransfer: DataTransfer) {
    const displayId = dataTransfer.getData("text/calendar-event-id");
    return events.find((event) => event.display_id === displayId);
  }

  function beginResize(
    pointerEvent: ReactPointerEvent<HTMLSpanElement>,
    event: DisplayCalendarEvent,
  ) {
    pointerEvent.preventDefault();
    pointerEvent.stopPropagation();
    const startY = Number.isFinite(pointerEvent.clientY)
      ? pointerEvent.clientY
      : 0;
    const originalEnd = new Date(event.end_at);

    function finishResize(endEvent: PointerEvent) {
      document.removeEventListener("pointerup", finishResize);
      const endY = Number.isFinite(endEvent.clientY)
        ? endEvent.clientY
        : startY;
      const minuteDelta = Math.round(((endY - startY) / HOUR_HEIGHT) * 4) * 15;
      const resizedEnd = new Date(originalEnd.getTime() + minuteDelta * 60_000);
      const minimumEnd = new Date(
        new Date(event.start_at).getTime() + 15 * 60_000,
      );
      onResize(event, resizedEnd < minimumEnd ? minimumEnd : resizedEnd);
    }

    document.addEventListener("pointerup", finishResize, { once: true });
  }

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

      <div
        className="all-day-grid"
        style={{ "--day-count": days.length } as CSSProperties}
      >
        <span className="all-day-label">All day</span>
        {days.map((day) => {
          const allDayEvents = eventsForDay(events, day).filter(
            (event) => event.all_day,
          ) as DisplayCalendarEvent[];
          return (
            <div
              className="all-day-column"
              key={dateKey(day)}
              onDragOver={(dragEvent) => dragEvent.preventDefault()}
              onDrop={(dragEvent) => {
                const dragged = draggedEvent(dragEvent.dataTransfer);
                if (dragged) onMove(dragged, day, false);
              }}
            >
              {allDayEvents.map((event) => {
                const calendar = calendars.get(event.calendar_id);
                const isReadOnly = calendar?.is_read_only ?? true;
                return (
                  <button
                    className={`all-day-event-chip status-${event.status}${
                      isReadOnly ? " protected-event" : ""
                    }`}
                    draggable={!isReadOnly}
                    key={`${dateKey(day)}:${event.display_id}`}
                    onClick={() => onSelectEvent(event)}
                    onDragStart={(dragEvent) => {
                      dragEvent.dataTransfer.effectAllowed = "move";
                      dragEvent.dataTransfer.setData(
                        "text/calendar-event-id",
                        event.display_id,
                      );
                    }}
                    style={
                      {
                        "--event-color": calendar?.color ?? "#29584c",
                      } as CSSProperties
                    }
                    type="button"
                  >
                    {isReadOnly && <span aria-hidden="true">🔒</span>}
                    <span>{event.title}</span>
                    {(event.series_id || event.recurrence_rule) && (
                      <span aria-label="Recurring event">↻</span>
                    )}
                  </button>
                );
              })}
            </div>
          );
        })}
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
            const dayEvents = eventsForDay(events, day).filter(
              (event) => !event.all_day,
            ) as DisplayCalendarEvent[];
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
                      onDragOver={(dragEvent) => dragEvent.preventDefault()}
                      onDrop={(dragEvent) => {
                        dragEvent.preventDefault();
                        const dragged = draggedEvent(dragEvent.dataTransfer);
                        if (dragged) onMove(dragged, slotDate, true);
                      }}
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
                  const isReadOnly = calendar?.is_read_only ?? true;
                  const position = clampEventToDay(event, day);
                  const style = {
                    "--event-color": calendar?.color ?? "#29584c",
                    top: position.top,
                    height: position.height,
                  } as CSSProperties;
                  return (
                    <button
                      aria-label={`${event.title}, ${formatEventTime(event)}${
                        isReadOnly ? ", read-only" : ""
                      }`}
                      className={`time-event status-${event.status}${
                        isReadOnly ? " protected-event" : ""
                      }`}
                      draggable={!isReadOnly}
                      key={`${dateKey(day)}:${event.display_id}`}
                      onClick={() => onSelectEvent(event)}
                      onDragStart={(dragEvent) => {
                        dragEvent.dataTransfer.effectAllowed = "move";
                        dragEvent.dataTransfer.setData(
                          "text/calendar-event-id",
                          event.display_id,
                        );
                      }}
                      style={style}
                      type="button"
                    >
                      <strong>
                        {event.title}
                        {(event.series_id || event.recurrence_rule) && " ↻"}
                      </strong>
                      <span>{formatEventTime(event)}</span>
                      {event.location && <small>{event.location}</small>}
                      {!isReadOnly && (
                        <span
                          aria-hidden="true"
                          className="event-resize-handle"
                          onPointerDown={(pointerEvent) =>
                            beginResize(pointerEvent, event)
                          }
                          title="Drag to resize"
                        />
                      )}
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
