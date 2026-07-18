import { useCallback, useEffect, useMemo, useState } from "react";

import { Icon } from "../../components/Icon";
import { calendarApi } from "./api";
import { CalendarDialog } from "./CalendarDialog";
import { CalendarFilters } from "./CalendarFilters";
import { CalendarList } from "./CalendarList";
import { CalendarToolbar } from "./CalendarToolbar";
import {
  addDays,
  getViewDays,
  getViewRange,
  moveAnchor,
  startOfDay,
} from "./dateUtils";
import { EventDialog } from "./EventDialog";
import { MonthView } from "./MonthView";
import { expandCalendarEvents } from "./recurrence";
import { TimeGridView } from "./TimeGridView";
import type {
  CalendarEvent,
  CalendarModel,
  CalendarMutation,
  CalendarView,
  DisplayCalendarEvent,
  EventFilters,
  EventMutation,
  RecurrenceScope,
} from "./types";

interface DialogState {
  draftDay: Date;
  event: DisplayCalendarEvent | null;
}

interface CalendarDialogState {
  calendar: CalendarModel | null;
}

const EMPTY_FILTERS: EventFilters = {
  search: "",
  calendarId: "",
  dateFrom: "",
  dateTo: "",
};

function messageFromError(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Teacher Assistant could not load the calendar right now.";
}

function filterDate(value: string): Date {
  return new Date(`${value}T00:00:00`);
}

function eventMatchesSearch(event: DisplayCalendarEvent, search: string) {
  const query = search.trim().toLocaleLowerCase();
  return (
    !query ||
    [event.title, event.description, event.location].some((value) =>
      (value ?? "").toLocaleLowerCase().includes(query),
    )
  );
}

function eventOverlaps(event: DisplayCalendarEvent, start: Date, end: Date) {
  return (
    new Date(event.start_at).getTime() < end.getTime() &&
    new Date(event.end_at).getTime() > start.getTime()
  );
}

export function CalendarPage() {
  const [view, setView] = useState<CalendarView>("month");
  const [anchor, setAnchor] = useState(() => new Date());
  const [calendars, setCalendars] = useState<CalendarModel[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [filters, setFilters] = useState<EventFilters>(EMPTY_FILTERS);
  const [isLoading, setIsLoading] = useState(true);
  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadVersion, setReloadVersion] = useState(0);
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const [calendarDialog, setCalendarDialog] =
    useState<CalendarDialogState | null>(null);

  const days = useMemo(() => getViewDays(anchor, view), [anchor, view]);
  const [rangeStart, rangeEnd] = useMemo(
    () => getViewRange(anchor, view),
    [anchor, view],
  );
  const [queryStart, queryEnd] = useMemo(() => {
    const start = filters.dateFrom ? filterDate(filters.dateFrom) : rangeStart;
    let end = filters.dateTo
      ? addDays(filterDate(filters.dateTo), 1)
      : rangeEnd;
    if (end <= start) end = addDays(start, 1);
    return [start, end];
  }, [filters.dateFrom, filters.dateTo, rangeEnd, rangeStart]);

  const loadCalendar = useCallback(
    async (signal?: AbortSignal) => {
      const [calendarResult, eventResult] = await Promise.all([
        calendarApi.listCalendars(signal),
        calendarApi.listEvents(queryEnd, queryStart, {
          calendarId: filters.calendarId || undefined,
          search: filters.search.trim() || undefined,
          signal,
        }),
      ]);
      setCalendars(calendarResult);
      setEvents(eventResult);
    },
    [filters.calendarId, filters.search, queryEnd, queryStart],
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
  const expandedEvents = useMemo(
    () => expandCalendarEvents(events, queryStart, queryEnd),
    [events, queryEnd, queryStart],
  );
  const filteredEvents = useMemo(
    () =>
      expandedEvents.filter(
        (event) =>
          (!filters.calendarId || event.calendar_id === filters.calendarId) &&
          eventMatchesSearch(event, filters.search),
      ),
    [expandedEvents, filters.calendarId, filters.search],
  );
  const visibleEvents = useMemo(
    () =>
      filteredEvents.filter(
        (event) =>
          visibleCalendarIds.has(event.calendar_id) &&
          eventOverlaps(event, rangeStart, rangeEnd),
      ),
    [filteredEvents, rangeEnd, rangeStart, visibleCalendarIds],
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

  function openEvent(event: DisplayCalendarEvent) {
    setDialog({ draftDay: new Date(event.start_at), event });
  }

  function selectSearchResult(event: DisplayCalendarEvent) {
    setAnchor(new Date(event.start_at));
    openEvent(event);
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

  async function handleCalendarSave(
    payload: CalendarMutation | Partial<CalendarMutation>,
    calendar: CalendarModel | null,
  ) {
    if (calendar) {
      await calendarApi.updateCalendar(calendar.id, payload);
    } else {
      await calendarApi.createCalendar(payload as CalendarMutation);
    }
    setCalendarDialog(null);
    setReloadVersion((version) => version + 1);
  }

  async function handleCalendarDelete(calendar: CalendarModel) {
    await calendarApi.deleteCalendar(calendar.id);
    setCalendarDialog(null);
    if (filters.calendarId === calendar.id) {
      setFilters((current) => ({ ...current, calendarId: "" }));
    } else {
      setReloadVersion((version) => version + 1);
    }
  }

  async function handleSave(
    payload: EventMutation,
    event: DisplayCalendarEvent | null,
    scope: RecurrenceScope | null,
  ) {
    if (!event) {
      await calendarApi.createEvent(payload);
    } else if (scope === "occurrence") {
      if (!event.series_id || !event.occurrence_start_at) {
        throw new Error("This recurring occurrence could not be identified.");
      }
      await calendarApi.updateEventOccurrence(
        event.series_id,
        event.occurrence_start_at,
        payload,
      );
    } else if (scope === "series") {
      await calendarApi.updateEventSeries(event.series_id ?? event.id, payload);
    } else {
      await calendarApi.updateEvent(event.id, payload);
    }
    setDialog(null);
    setReloadVersion((version) => version + 1);
  }

  async function handleDelete(
    event: DisplayCalendarEvent,
    scope: RecurrenceScope | null,
  ) {
    if (scope === "occurrence") {
      if (!event.series_id || !event.occurrence_start_at) {
        throw new Error("This recurring occurrence could not be identified.");
      }
      await calendarApi.deleteEventOccurrence(
        event.series_id,
        event.occurrence_start_at,
      );
    } else if (scope === "series") {
      await calendarApi.deleteEventSeries(event.series_id ?? event.id);
    } else {
      await calendarApi.deleteEvent(event.id);
    }
    setDialog(null);
    setReloadVersion((version) => version + 1);
  }

  function ensureEventWritable(event: DisplayCalendarEvent) {
    const calendar = calendarMap.get(event.calendar_id);
    if (!calendar || calendar.is_read_only) {
      setError("This calendar is read-only and cannot be modified.");
      return false;
    }
    return true;
  }

  async function persistDirectInteraction(
    event: DisplayCalendarEvent,
    changes: Partial<EventMutation>,
  ) {
    if (!ensureEventWritable(event)) return;
    setError(null);
    try {
      if (event.series_id && event.occurrence_start_at) {
        await calendarApi.updateEventOccurrence(
          event.series_id,
          event.occurrence_start_at,
          changes,
        );
      } else {
        await calendarApi.updateEvent(event.id, changes);
      }
      setReloadVersion((version) => version + 1);
    } catch (interactionError) {
      setError(messageFromError(interactionError));
    }
  }

  function handleMove(
    event: DisplayCalendarEvent,
    target: Date,
    useTargetTime: boolean,
  ) {
    if (!ensureEventWritable(event)) return;
    const oldStart = new Date(event.start_at);
    const oldEnd = new Date(event.end_at);
    const duration = oldEnd.getTime() - oldStart.getTime();
    const newStart = new Date(target);
    if (event.all_day) {
      newStart.setHours(0, 0, 0, 0);
    } else if (!useTargetTime) {
      newStart.setHours(
        oldStart.getHours(),
        oldStart.getMinutes(),
        oldStart.getSeconds(),
        0,
      );
    }
    const newEnd = new Date(newStart.getTime() + duration);
    void persistDirectInteraction(event, {
      start_at: newStart.toISOString(),
      end_at: newEnd.toISOString(),
    });
  }

  function handleResize(event: DisplayCalendarEvent, endAt: Date) {
    if (!ensureEventWritable(event)) return;
    void persistDirectInteraction(event, { end_at: endAt.toISOString() });
  }

  const noVisibleCalendars =
    calendars.length > 0 && visibleCalendarIds.size === 0;
  const noEvents =
    calendars.length > 0 &&
    visibleCalendarIds.size > 0 &&
    visibleEvents.length === 0;
  const seriesEvent = dialog?.event?.series_id
    ? (events.find((event) => event.id === dialog.event?.series_id) ?? null)
    : dialog?.event?.recurrence_rule
      ? (events.find((event) => event.id === dialog.event?.id) ?? null)
      : null;

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

      <CalendarFilters
        calendars={calendars}
        filters={filters}
        onChange={setFilters}
        onSelectEvent={selectSearchResult}
        results={filteredEvents}
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
          onCreate={() => setCalendarDialog({ calendar: null })}
          onManage={(calendar) => setCalendarDialog({ calendar })}
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
                  onMove={(event, day) => handleMove(event, day, false)}
                  onSelectEvent={openEvent}
                />
              ) : (
                <TimeGridView
                  calendars={calendarMap}
                  days={days}
                  events={visibleEvents}
                  onCreate={openCreate}
                  onMove={handleMove}
                  onResize={handleResize}
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
          key={dialog.event?.display_id ?? dialog.draftDay.toISOString()}
          onClose={() => setDialog(null)}
          onDelete={handleDelete}
          onSave={handleSave}
          seriesEvent={seriesEvent}
        />
      )}

      {calendarDialog && (
        <CalendarDialog
          calendar={calendarDialog.calendar}
          key={calendarDialog.calendar?.id ?? "new-calendar"}
          onClose={() => setCalendarDialog(null)}
          onDelete={handleCalendarDelete}
          onSave={handleCalendarSave}
        />
      )}
    </main>
  );
}
