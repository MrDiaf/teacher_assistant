import { useCallback, useEffect, useMemo, useState } from "react";

import { Icon } from "../../components/Icon";
import { calendarApi } from "./api";
import { CalendarList } from "./CalendarList";
import { CalendarToolbar } from "./CalendarToolbar";
import { getViewDays, getViewRange, moveAnchor, startOfDay } from "./dateUtils";
import { EventDialog } from "./EventDialog";
import { MonthView } from "./MonthView";
import { TimeGridView } from "./TimeGridView";
import type {
  CalendarEvent,
  CalendarModel,
  CalendarView,
  EventMutation,
} from "./types";

interface DialogState {
  draftDay: Date;
  event: CalendarEvent | null;
}

function messageFromError(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Teacher Assistant could not load the calendar right now.";
}

export function CalendarPage() {
  const [view, setView] = useState<CalendarView>("month");
  const [anchor, setAnchor] = useState(() => new Date());
  const [calendars, setCalendars] = useState<CalendarModel[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadVersion, setReloadVersion] = useState(0);
  const [dialog, setDialog] = useState<DialogState | null>(null);

  const days = useMemo(() => getViewDays(anchor, view), [anchor, view]);
  const [rangeStart, rangeEnd] = useMemo(
    () => getViewRange(anchor, view),
    [anchor, view],
  );

  const loadCalendar = useCallback(
    async (signal?: AbortSignal) => {
      const [calendarResult, eventResult] = await Promise.all([
        calendarApi.listCalendars(signal),
        calendarApi.listEvents(rangeEnd, rangeStart, signal),
      ]);
      setCalendars(calendarResult);
      setEvents(eventResult);
    },
    [rangeEnd, rangeStart],
  );

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    loadCalendar(controller.signal)
      .catch((loadError: unknown) => {
        if (
          !(
            loadError instanceof DOMException && loadError.name === "AbortError"
          )
        ) {
          setError(messageFromError(loadError));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      });
    return () => controller.abort();
  }, [loadCalendar, reloadVersion]);

  const calendarMap = useMemo(
    () => new Map(calendars.map((calendar) => [calendar.id, calendar])),
    [calendars],
  );
  const visibleCalendarIds = useMemo(
    () =>
      new Set(
        calendars
          .filter((calendar) => calendar.is_visible)
          .map((calendar) => calendar.id),
      ),
    [calendars],
  );
  const visibleEvents = useMemo(
    () => events.filter((event) => visibleCalendarIds.has(event.calendar_id)),
    [events, visibleCalendarIds],
  );
  const writableCalendars = calendars.filter(
    (calendar) => !calendar.is_read_only,
  );

  function openCreate(day: Date) {
    if (writableCalendars.length === 0) {
      setError("Add a writable calendar before creating an event.");
      return;
    }
    setDialog({ draftDay: new Date(day), event: null });
  }

  function openEvent(event: CalendarEvent) {
    setDialog({ draftDay: new Date(event.start_at), event });
  }

  async function handleVisibilityChange(
    calendar: CalendarModel,
    visible: boolean,
  ) {
    setError(null);
    setCalendars((current) =>
      current.map((item) =>
        item.id === calendar.id ? { ...item, is_visible: visible } : item,
      ),
    );
    try {
      const updated = await calendarApi.updateCalendarVisibility(
        calendar.id,
        visible,
      );
      setCalendars((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (visibilityError) {
      setCalendars((current) =>
        current.map((item) => (item.id === calendar.id ? calendar : item)),
      );
      setError(messageFromError(visibilityError));
    }
  }

  async function handleBootstrap() {
    setIsBootstrapping(true);
    setError(null);
    try {
      await calendarApi.createDefaultCalendar();
      await loadCalendar();
    } catch (bootstrapError) {
      setError(messageFromError(bootstrapError));
    } finally {
      setIsBootstrapping(false);
    }
  }

  async function handleSave(
    payload: EventMutation,
    event: CalendarEvent | null,
  ) {
    if (event) {
      await calendarApi.updateEvent(event.id, payload);
    } else {
      await calendarApi.createEvent(payload);
    }
    setDialog(null);
    setReloadVersion((version) => version + 1);
  }

  async function handleDelete(event: CalendarEvent) {
    await calendarApi.deleteEvent(event.id);
    setDialog(null);
    setReloadVersion((version) => version + 1);
  }

  const noVisibleCalendars =
    calendars.length > 0 && visibleCalendarIds.size === 0;
  const noEvents =
    calendars.length > 0 &&
    visibleCalendarIds.size > 0 &&
    visibleEvents.length === 0;

  return (
    <main className="calendar-page">
      <CalendarToolbar
        anchor={anchor}
        canCreate={writableCalendars.length > 0}
        onCreate={() => openCreate(startOfDay(anchor))}
        onMove={(direction) =>
          setAnchor((current) => moveAnchor(current, view, direction))
        }
        onToday={() => setAnchor(new Date())}
        onViewChange={setView}
        view={view}
      />

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <div>
            <button
              className="text-button"
              onClick={() => setReloadVersion((version) => version + 1)}
              type="button"
            >
              <Icon name="refresh" size={15} /> Retry
            </button>
            <button
              aria-label="Dismiss error"
              onClick={() => setError(null)}
              type="button"
            >
              <Icon name="x" size={16} />
            </button>
          </div>
        </div>
      )}

      <div className="calendar-workspace">
        <CalendarList
          calendars={calendars}
          isBootstrapping={isBootstrapping}
          isLoading={isLoading && calendars.length === 0}
          onBootstrap={handleBootstrap}
          onVisibilityChange={handleVisibilityChange}
        />

        <div className="calendar-canvas">
          {isLoading && calendars.length === 0 ? (
            <div className="calendar-loading" aria-label="Loading calendar">
              <span />
              <span />
              <span />
              <span />
            </div>
          ) : calendars.length === 0 ? (
            <div className="main-empty-state">
              <span className="empty-symbol large">
                <Icon name="calendar" size={28} />
              </span>
              <p className="eyebrow">A clear place to begin</p>
              <h2>Set up your first calendar</h2>
              <p>
                Create a private Personal calendar, then add your first event.
              </p>
              <button
                className="primary-button"
                disabled={isBootstrapping}
                onClick={handleBootstrap}
                type="button"
              >
                <Icon name="plus" size={18} />
                {isBootstrapping ? "Setting up…" : "Set up calendar"}
              </button>
            </div>
          ) : (
            <div className="calendar-view-frame">
              {noVisibleCalendars && (
                <div className="calendar-state-callout">
                  <strong>All calendars are hidden</strong>
                  <span>Turn one on from My calendars to see its events.</span>
                </div>
              )}
              {noEvents && !isLoading && (
                <div className="calendar-state-callout subtle">
                  <strong>No events in this date range</strong>
                  <span>Select a day or use Create event to add one.</span>
                </div>
              )}
              {view === "month" ? (
                <MonthView
                  anchor={anchor}
                  calendars={calendarMap}
                  days={days}
                  events={visibleEvents}
                  onCreate={openCreate}
                  onSelectEvent={openEvent}
                />
              ) : (
                <TimeGridView
                  calendars={calendarMap}
                  days={days}
                  events={visibleEvents}
                  onCreate={openCreate}
                  onSelectEvent={openEvent}
                  view={view}
                />
              )}
            </div>
          )}
        </div>
      </div>

      {dialog && (
        <EventDialog
          calendars={calendars}
          draftDay={dialog.draftDay}
          event={dialog.event}
          key={dialog.event?.id ?? dialog.draftDay.toISOString()}
          onClose={() => setDialog(null)}
          onDelete={handleDelete}
          onSave={handleSave}
        />
      )}
    </main>
  );
}
