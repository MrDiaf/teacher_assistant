import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { Icon } from "../../platform/ui";
import {
  CalendarWorkspace,
  type CalendarSidebarRenderProps,
} from "../calendar/CalendarPage";
import { calendarApi } from "../calendar/api";
import type { CalendarModel } from "../calendar/types";
import { courseApi } from "./api";
import type { CourseModel } from "./types";

interface CourseCalendarProps {
  course: CourseModel;
  onCalendarCountChange: (count: number) => void;
}

interface CourseCalendarSidebarProps extends CalendarSidebarRenderProps {
  allCalendars: CalendarModel[];
  allCalendarsError: string | null;
  availableCalendars: CalendarModel[];
  busyCalendarId: string | null;
  isLinking: boolean;
  linkSelection: string;
  linkSelectRef: React.RefObject<HTMLSelectElement | null>;
  onLink: (event: FormEvent<HTMLFormElement>) => void;
  onLinkSelectionChange: (calendarId: string) => void;
  onUnlink: (calendar: CalendarModel) => void;
}

function calendarKind(calendar: CalendarModel) {
  if (calendar.is_subscribed) return "Subscribed";
  if (calendar.source_type === "ics_import") return "Imported";
  return "Local";
}

function CourseCalendarSidebar({
  allCalendars,
  allCalendarsError,
  availableCalendars,
  busyCalendarId,
  calendars,
  isLinking,
  isLoading,
  linkSelection,
  linkSelectRef,
  onLink,
  onLinkSelectionChange,
  onUnlink,
  onVisibilityChange,
}: CourseCalendarSidebarProps) {
  return (
    <aside
      aria-label="Course calendars"
      className="calendar-list-panel course-calendar-sidebar"
    >
      <div className="calendar-list-heading">
        <div>
          <p className="eyebrow">Course schedule</p>
          <h2>Linked calendars</h2>
        </div>
        <span className="calendar-count">{calendars.length}</span>
      </div>

      <form className="course-calendar-link-form" onSubmit={onLink}>
        <label>
          <span>Calendar to link</span>
          <select
            disabled={availableCalendars.length === 0 || isLinking}
            onChange={(event) => onLinkSelectionChange(event.target.value)}
            ref={linkSelectRef}
            value={linkSelection}
          >
            {availableCalendars.length === 0 ? (
              <option value="">
                {allCalendars.length === 0
                  ? "No calendars available"
                  : "All calendars are linked"}
              </option>
            ) : (
              availableCalendars.map((calendar) => (
                <option key={calendar.id} value={calendar.id}>
                  {calendar.name}
                  {calendar.is_read_only ? " · Read-only" : ""}
                </option>
              ))
            )}
          </select>
        </label>
        <button
          className="primary-button"
          disabled={!linkSelection || isLinking}
          type="submit"
        >
          <Icon name="plus" size={15} />
          {isLinking ? "Linking…" : "Link calendar"}
        </button>
      </form>

      {allCalendarsError && (
        <p className="course-calendar-sidebar-error" role="alert">
          {allCalendarsError}
        </p>
      )}

      {isLoading ? (
        <div className="calendar-list-skeleton" aria-label="Loading calendars">
          <span />
          <span />
          <span />
        </div>
      ) : calendars.length === 0 ? (
        <div className="course-calendar-list-empty">
          <Icon name="calendar" size={21} />
          <strong>No calendars linked</strong>
          <p>Link an existing calendar to show its events in this course.</p>
        </div>
      ) : (
        <div className="calendar-options">
          {calendars.map((calendar) => (
            <div
              className={`calendar-option course-calendar-option${
                calendar.is_read_only ? " protected" : ""
              }`}
              key={calendar.id}
            >
              <label>
                <input
                  aria-label={`Show ${calendar.name}`}
                  checked={calendar.is_visible}
                  onChange={(event) =>
                    void onVisibilityChange(calendar, event.target.checked)
                  }
                  type="checkbox"
                />
                <span
                  className="calendar-color"
                  style={{ backgroundColor: calendar.color }}
                />
                <span className="calendar-option-copy">
                  <strong>{calendar.name}</strong>
                  <small>
                    {calendarKind(calendar)}
                    {calendar.is_read_only ? " · Read-only" : ""}
                  </small>
                </span>
              </label>
              {calendar.is_read_only && (
                <span className="read-only-icon" title="Read-only calendar">
                  <Icon name="lock" size={14} />
                </span>
              )}
              <button
                aria-label={`Unlink ${calendar.name}`}
                className="course-calendar-unlink"
                disabled={busyCalendarId === calendar.id}
                onClick={() => onUnlink(calendar)}
                title="Unlink calendar without deleting it"
                type="button"
              >
                <Icon name="x" size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="calendar-list-note">
        <Icon name="lock" size={15} />
        <span>
          Visibility is shared with Calendar. Unlinking never deletes calendars
          or events, and read-only calendars stay protected.
        </span>
      </div>
    </aside>
  );
}

export function CourseCalendar({
  course,
  onCalendarCountChange,
}: CourseCalendarProps) {
  const [allCalendars, setAllCalendars] = useState<CalendarModel[]>([]);
  const [allCalendarsError, setAllCalendarsError] = useState<string | null>(
    null,
  );
  const [linkedCalendarIds, setLinkedCalendarIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [linkSelection, setLinkSelection] = useState("");
  const [isLinking, setIsLinking] = useState(false);
  const [busyCalendarId, setBusyCalendarId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const linkSelectRef = useRef<HTMLSelectElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    setAllCalendarsError(null);
    calendarApi
      .listCalendars(controller.signal)
      .then(setAllCalendars)
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setAllCalendarsError(
            error instanceof Error
              ? error.message
              : "Available calendars could not be loaded.",
          );
        }
      });
    return () => controller.abort();
  }, []);

  const loadLinkedCalendars = useCallback(
    async (signal?: AbortSignal) => {
      const calendars = await courseApi.listCalendars(course.id, signal);
      setLinkedCalendarIds((current) => {
        const next = new Set(calendars.map((calendar) => calendar.id));
        if (
          current.size === next.size &&
          [...current].every((calendarId) => next.has(calendarId))
        ) {
          return current;
        }
        return next;
      });
      onCalendarCountChange(calendars.length);
      return calendars;
    },
    [course.id, onCalendarCountChange],
  );

  const loadCourseEvents = useCallback(
    (
      startsBefore: Date,
      endsAfter: Date,
      options?: {
        calendarId?: string;
        search?: string;
        signal?: AbortSignal;
      },
    ) => {
      const calendarId =
        options?.calendarId && linkedCalendarIds.has(options.calendarId)
          ? options.calendarId
          : undefined;
      return courseApi.listEvents(course.id, startsBefore, endsAfter, {
        ...options,
        calendarId,
      });
    },
    [course.id, linkedCalendarIds],
  );

  const availableCalendars = useMemo(
    () =>
      allCalendars.filter((calendar) => !linkedCalendarIds.has(calendar.id)),
    [allCalendars, linkedCalendarIds],
  );

  useEffect(() => {
    if (
      linkSelection &&
      availableCalendars.some((calendar) => calendar.id === linkSelection)
    ) {
      return;
    }
    setLinkSelection(availableCalendars[0]?.id ?? "");
  }, [availableCalendars, linkSelection]);

  async function handleLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!linkSelection || isLinking) return;
    setIsLinking(true);
    setActionError(null);
    try {
      await courseApi.linkCalendar(course.id, linkSelection);
      setLinkedCalendarIds((current) => {
        const next = new Set(current);
        next.add(linkSelection);
        return next;
      });
      setReloadToken((token) => token + 1);
    } catch (error) {
      setActionError(
        error instanceof Error
          ? error.message
          : "The calendar could not be linked.",
      );
    } finally {
      setIsLinking(false);
    }
  }

  async function handleUnlink(calendar: CalendarModel) {
    setBusyCalendarId(calendar.id);
    setActionError(null);
    try {
      await courseApi.unlinkCalendar(course.id, calendar.id);
      setLinkedCalendarIds((current) => {
        const next = new Set(current);
        next.delete(calendar.id);
        return next;
      });
      setReloadToken((token) => token + 1);
    } catch (error) {
      setActionError(
        error instanceof Error
          ? error.message
          : "The calendar could not be unlinked.",
      );
    } finally {
      setBusyCalendarId(null);
    }
  }

  return (
    <div className="course-calendar">
      {actionError && (
        <div className="course-materials-error" role="alert">
          {actionError}
        </div>
      )}
      <CalendarWorkspace
        embedded
        emptyState={
          <div className="main-empty-state course-calendar-empty">
            <span className="empty-symbol large">
              <Icon name="calendar" size={28} />
            </span>
            <p className="eyebrow">Course calendar</p>
            <h2>No calendars linked yet</h2>
            <p>
              Link an existing calendar to see its events here. Calendar data
              stays in the Calendar module.
            </p>
            <button
              className="primary-button"
              disabled={availableCalendars.length === 0}
              onClick={() => linkSelectRef.current?.focus()}
              type="button"
            >
              <Icon name="plus" size={17} /> Link calendar
            </button>
          </div>
        }
        eyebrow={`${course.course_code ?? course.name} schedule`}
        loadCalendars={loadLinkedCalendars}
        loadEvents={loadCourseEvents}
        persistenceCourseId={course.id}
        reloadToken={reloadToken}
        renderSidebar={(sidebarProps) => (
          <CourseCalendarSidebar
            {...sidebarProps}
            allCalendars={allCalendars}
            allCalendarsError={allCalendarsError}
            availableCalendars={availableCalendars}
            busyCalendarId={busyCalendarId}
            isLinking={isLinking}
            linkSelection={linkSelection}
            linkSelectRef={linkSelectRef}
            onLink={(event) => void handleLink(event)}
            onLinkSelectionChange={setLinkSelection}
            onUnlink={(calendar) => void handleUnlink(calendar)}
          />
        )}
      />
    </div>
  );
}
