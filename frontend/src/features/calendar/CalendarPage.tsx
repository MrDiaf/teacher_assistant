import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  getCalendarPreference,
  setCalendarPreference,
} from "../../platform/persistence";
import { Icon } from "../../platform/ui";
import { calendarApi } from "./api";
import { CalendarDialog } from "./CalendarDialog";
import { CalendarFilters } from "./CalendarFilters";
import { CalendarList } from "./CalendarList";
import { CalendarToolbar } from "./CalendarToolbar";
import {
  addDays,
  dateKey,
  getViewDays,
  getViewRange,
  moveAnchor,
  startOfDay,
} from "./dateUtils";
import { EventDialog } from "./EventDialog";
import { IcsImportDialog } from "./IcsImportDialog";
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

interface UndoState {
  id: number;
  message: string;
  action: () => Promise<unknown>;
  isRunning: boolean;
}

export interface CalendarSidebarRenderProps {
  calendars: CalendarModel[];
  isLoading: boolean;
  onVisibilityChange: (
    calendar: CalendarModel,
    visible: boolean,
  ) => Promise<void>;
}

interface CalendarWorkspaceProps {
  embedded?: boolean;
  emptyState?: ReactNode;
  eyebrow?: string;
  loadCalendars?: (signal?: AbortSignal) => Promise<CalendarModel[]>;
  loadEvents?: (
    startsBefore: Date,
    endsAfter: Date,
    options?: {
      calendarId?: string;
      search?: string;
      signal?: AbortSignal;
    },
  ) => Promise<CalendarEvent[]>;
  persistenceCourseId?: string;
  reloadToken?: number;
  renderSidebar?: (props: CalendarSidebarRenderProps) => ReactNode;
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

function eventMutationFrom(event: CalendarEvent): EventMutation {
  return {
    calendar_id: event.calendar_id,
    title: event.title,
    description: event.description,
    location: event.location,
    start_at: event.start_at,
    end_at: event.end_at,
    all_day: event.all_day,
    timezone: event.timezone,
    recurrence_rule: event.recurrence_rule,
    status: event.status,
  };
}

function calendarMutationFrom(calendar: CalendarModel): CalendarMutation {
  return {
    name: calendar.name,
    description: calendar.description,
    color: calendar.color,
    is_visible: calendar.is_visible,
    is_read_only: calendar.is_read_only,
  };
}

export function CalendarWorkspace({
  embedded = false,
  emptyState,
  eyebrow = "Personal schedule",
  loadCalendars = calendarApi.listCalendars,
  loadEvents = calendarApi.listEvents,
  persistenceCourseId,
  reloadToken = 0,
  renderSidebar,
}: CalendarWorkspaceProps) {
  const [initialPreference] = useState(() =>
    getCalendarPreference(persistenceCourseId),
  );
  const [view, setView] = useState<CalendarView>(
    () => initialPreference?.view ?? "month",
  );
  const [anchor, setAnchor] = useState(() =>
    initialPreference
      ? new Date(`${initialPreference.anchor}T00:00:00`)
      : new Date(),
  );
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
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [undoState, setUndoState] = useState<UndoState | null>(null);

  useEffect(() => {
    setCalendarPreference(
      { view, anchor: dateKey(anchor) },
      persistenceCourseId,
    );
  }, [anchor, persistenceCourseId, view]);

  useEffect(() => {
    if (!undoState || undoState.isRunning) return;
    const timeout = window.setTimeout(() => setUndoState(null), 12_000);
    return () => window.clearTimeout(timeout);
  }, [undoState?.id, undoState?.isRunning]);

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
        loadCalendars(signal),
        loadEvents(queryEnd, queryStart, {
          calendarId: filters.calendarId || undefined,
          search: filters.search.trim() || undefined,
          signal,
        }),
      ]);
      setCalendars(calendarResult);
      setEvents(eventResult);
    },
    [
      filters.calendarId,
      filters.search,
      loadCalendars,
      loadEvents,
      queryEnd,
      queryStart,
    ],
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
  }, [loadCalendar, reloadToken, reloadVersion]);

  const calendarMap = useMemo(
    () => new Map(calendars.map((calendar) => [calendar.id, calendar])),
    [calendars],
  );
  useEffect(() => {
    if (
      !isLoading &&
      filters.calendarId &&
      !calendarMap.has(filters.calendarId)
    ) {
      setFilters((current) => ({ ...current, calendarId: "" }));
    }
  }, [calendarMap, filters.calendarId, isLoading]);
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
      const updated = await calendarApi.updateCalendar(calendar.id, payload);
      offerUndo("Calendar changes saved.", async () => {
        if (updated.is_read_only && !calendar.is_read_only) {
          await calendarApi.updateCalendar(calendar.id, {
            is_read_only: false,
          });
        }
        await calendarApi.updateCalendar(
          calendar.id,
          calendarMutationFrom(calendar),
        );
      });
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
      const created = await calendarApi.createEvent(payload);
      offerUndo("Event created.", () => calendarApi.deleteEvent(created.id));
    } else if (scope === "occurrence") {
      if (!event.series_id || !event.occurrence_start_at) {
        throw new Error("This recurring occurrence could not be identified.");
      }
      await calendarApi.updateEventOccurrence(
        event.series_id,
        event.occurrence_start_at,
        payload,
      );
      const previous = eventMutationFrom(event);
      offerUndo("Occurrence updated.", () =>
        calendarApi.updateEventOccurrence(
          event.series_id!,
          event.occurrence_start_at!,
          previous,
        ),
      );
    } else if (scope === "series") {
      const seriesId = event.series_id ?? event.id;
      await calendarApi.updateEventSeries(seriesId, payload);
      const previous = eventMutationFrom(seriesEvent ?? event);
      offerUndo("Series updated.", () =>
        calendarApi.updateEventSeries(seriesId, previous),
      );
    } else {
      await calendarApi.updateEvent(event.id, payload);
      const previous = eventMutationFrom(event);
      offerUndo("Event updated.", () =>
        calendarApi.updateEvent(event.id, previous),
      );
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
      const previous = eventMutationFrom(event);
      offerUndo("Occurrence deleted.", () =>
        calendarApi.updateEventOccurrence(
          event.series_id!,
          event.occurrence_start_at!,
          previous,
        ),
      );
    } else if (scope === "series") {
      await calendarApi.deleteEventSeries(event.series_id ?? event.id);
    } else {
      await calendarApi.deleteEvent(event.id);
      const previous = eventMutationFrom(event);
      offerUndo("Event deleted.", () => calendarApi.createEvent(previous));
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
      const previous = Object.fromEntries(
        Object.keys(changes).map((field) => [
          field,
          event[field as keyof DisplayCalendarEvent],
        ]),
      ) as Partial<EventMutation>;
      if (event.series_id && event.occurrence_start_at) {
        await calendarApi.updateEventOccurrence(
          event.series_id,
          event.occurrence_start_at,
          changes,
        );
        offerUndo("Occurrence moved.", () =>
          calendarApi.updateEventOccurrence(
            event.series_id!,
            event.occurrence_start_at!,
            previous,
          ),
        );
      } else {
        await calendarApi.updateEvent(event.id, changes);
        offerUndo("Event changed.", () =>
          calendarApi.updateEvent(event.id, previous),
        );
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

  function offerUndo(message: string, action: () => Promise<unknown>) {
    setUndoState({ id: Date.now(), message, action, isRunning: false });
  }

  async function runUndo() {
    if (!undoState || undoState.isRunning) return;
    const current = undoState;
    setUndoState({ ...current, isRunning: true });
    setError(null);
    try {
      await current.action();
      setUndoState(null);
      setReloadVersion((version) => version + 1);
    } catch (undoError) {
      setError(messageFromError(undoError));
      setUndoState({ ...current, isRunning: false });
    }
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

  const Root = embedded ? "div" : "main";
  const headingId = embedded
    ? "course-calendar-workspace-heading"
    : "calendar-page-title";

  return (
    <Root
      aria-labelledby={headingId}
      className={`calendar-page${embedded ? " embedded-calendar-page" : ""}`}
    >
      <CalendarToolbar
        anchor={anchor}
        canCreate={writableCalendars.length > 0}
        eyebrow={eyebrow}
        headingId={headingId}
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
        {renderSidebar ? (
          renderSidebar({
            calendars,
            isLoading: isLoading && calendars.length === 0,
            onVisibilityChange: handleVisibilityChange,
          })
        ) : (
          <CalendarList
            calendars={calendars}
            isBootstrapping={isBootstrapping}
            isLoading={isLoading && calendars.length === 0}
            onBootstrap={handleBootstrap}
            onCreate={() => setCalendarDialog({ calendar: null })}
            onImport={() => setIsImportOpen(true)}
            onManage={(calendar) => setCalendarDialog({ calendar })}
            onVisibilityChange={handleVisibilityChange}
          />
        )}

        <div className="calendar-canvas">
          {isLoading && calendars.length === 0 ? (
            <div
              className="calendar-loading"
              aria-label="Loading calendar"
              role="status"
            >
              <span />
              <span />
              <span />
              <span />
            </div>
          ) : calendars.length === 0 ? (
            (emptyState ?? (
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
            ))
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

      {isImportOpen && (
        <IcsImportDialog
          calendars={calendars}
          onClose={() => setIsImportOpen(false)}
          onImported={() => setReloadVersion((version) => version + 1)}
        />
      )}

      {undoState && (
        <div className="undo-toast" role="status" aria-live="polite">
          <span>{undoState.message}</span>
          <button
            disabled={undoState.isRunning}
            onClick={() => void runUndo()}
            type="button"
          >
            {undoState.isRunning ? "Undoing…" : "Undo"}
          </button>
          <button
            aria-label="Dismiss undo notification"
            disabled={undoState.isRunning}
            onClick={() => setUndoState(null)}
            type="button"
          >
            <Icon name="x" size={15} />
          </button>
        </div>
      )}
    </Root>
  );
}

export function CalendarPage() {
  return <CalendarWorkspace />;
}
