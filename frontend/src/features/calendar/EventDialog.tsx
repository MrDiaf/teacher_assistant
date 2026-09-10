import { useState, type FormEvent } from "react";

import { Icon, useModalDialog } from "../../platform/ui";
import { addDays, defaultEventWindow, toDateTimeLocal } from "./dateUtils";
import { recurrenceLabel } from "./recurrence";
import type {
  CalendarEvent,
  CalendarModel,
  DisplayCalendarEvent,
  EventMutation,
  EventStatus,
  RecurrenceScope,
} from "./types";

type RepeatOption = "none" | "daily" | "weekly" | "monthly";

interface EventDialogProps {
  calendars: CalendarModel[];
  draftDay: Date;
  event: DisplayCalendarEvent | null;
  seriesEvent: CalendarEvent | null;
  onClose: () => void;
  onDelete: (
    event: DisplayCalendarEvent,
    scope: RecurrenceScope | null,
  ) => Promise<void>;
  onSave: (
    payload: EventMutation,
    event: DisplayCalendarEvent | null,
    scope: RecurrenceScope | null,
  ) => Promise<void>;
}

function toDateInput(value: string | Date): string {
  return toDateTimeLocal(value).slice(0, 10);
}

function repeatFromRule(rule: string | null | undefined): RepeatOption {
  if (rule?.includes("FREQ=DAILY")) return "daily";
  if (rule?.includes("FREQ=WEEKLY")) return "weekly";
  if (rule?.includes("FREQ=MONTHLY")) return "monthly";
  return "none";
}

function ruleFromRepeat(repeat: RepeatOption): string | null {
  if (repeat === "none") return null;
  return `FREQ=${repeat.toUpperCase()}`;
}

export function EventDialog({
  calendars,
  draftDay,
  event,
  seriesEvent,
  onClose,
  onDelete,
  onSave,
}: EventDialogProps) {
  const writableCalendars = calendars.filter(
    (calendar) => !calendar.is_read_only,
  );
  const eventCalendar = calendars.find(
    (calendar) => calendar.id === event?.calendar_id,
  );
  const isReadOnly = Boolean(event && eventCalendar?.is_read_only);
  const isRecurring = Boolean(
    event && (event.series_id || event.recurrence_rule),
  );
  const [defaultStart, defaultEnd] = defaultEventWindow(draftDay);
  const [scope, setScope] = useState<RecurrenceScope>("occurrence");
  const [calendarId, setCalendarId] = useState(
    event?.calendar_id ?? writableCalendars[0]?.id ?? "",
  );
  const [title, setTitle] = useState(event?.title ?? "");
  const [description, setDescription] = useState(event?.description ?? "");
  const [location, setLocation] = useState(event?.location ?? "");
  const [allDay, setAllDay] = useState(event?.all_day ?? false);
  const [startAt, setStartAt] = useState(
    event?.all_day
      ? toDateInput(event.start_at)
      : toDateTimeLocal(event?.start_at ?? defaultStart),
  );
  const [endAt, setEndAt] = useState(
    event?.all_day
      ? toDateInput(event.end_at)
      : toDateTimeLocal(event?.end_at ?? defaultEnd),
  );
  const [repeat, setRepeat] = useState<RepeatOption>(
    repeatFromRule(seriesEvent?.recurrence_rule ?? event?.recurrence_rule),
  );
  const [status, setStatus] = useState<EventStatus>(
    event?.status ?? "confirmed",
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useModalDialog(onClose);

  function loadEventValues(source: CalendarEvent) {
    setCalendarId(source.calendar_id);
    setTitle(source.title);
    setDescription(source.description ?? "");
    setLocation(source.location ?? "");
    setAllDay(source.all_day);
    setStartAt(
      source.all_day
        ? toDateInput(source.start_at)
        : toDateTimeLocal(source.start_at),
    );
    setEndAt(
      source.all_day
        ? toDateInput(source.end_at)
        : toDateTimeLocal(source.end_at),
    );
    setStatus(source.status);
    setRepeat(repeatFromRule(source.recurrence_rule));
  }

  function handleScopeChange(nextScope: RecurrenceScope) {
    setScope(nextScope);
    if (nextScope === "series" && seriesEvent) {
      loadEventValues(seriesEvent);
    } else if (event) {
      loadEventValues(event);
    }
  }

  function handleAllDayChange(nextAllDay: boolean) {
    if (nextAllDay) {
      const startDate = new Date(startAt);
      const endDate = new Date(endAt);
      const startDateText = toDateInput(startDate);
      const endDateText = toDateInput(endDate);
      setStartAt(startDateText);
      setEndAt(
        toDateInput(
          endDateText <= startDateText ? addDays(startDate, 1) : endDate,
        ),
      );
    } else {
      const start = new Date(`${startAt}T09:00:00`);
      const end = new Date(`${endAt}T10:00:00`);
      setStartAt(toDateTimeLocal(start));
      setEndAt(toDateTimeLocal(end <= start ? addDays(start, 1) : end));
    }
    setAllDay(nextAllDay);
  }

  async function handleSubmit(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault();
    setError(null);

    if (!calendarId) {
      setError("Choose a writable calendar first.");
      return;
    }
    if (!title.trim()) {
      setError("Add a title for the event.");
      return;
    }

    const start = new Date(allDay ? `${startAt}T00:00:00` : startAt);
    const end = new Date(allDay ? `${endAt}T00:00:00` : endAt);
    if (
      Number.isNaN(start.getTime()) ||
      Number.isNaN(end.getTime()) ||
      end <= start
    ) {
      setError(
        allDay
          ? "The exclusive end date must be later than the start date."
          : "The end time must be later than the start time.",
      );
      return;
    }

    setIsSaving(true);
    try {
      await onSave(
        {
          calendar_id: calendarId,
          title: title.trim(),
          description: description.trim() || null,
          location: location.trim() || null,
          start_at: start.toISOString(),
          end_at: end.toISOString(),
          all_day: allDay,
          timezone: "Europe/Stockholm",
          recurrence_rule:
            !event || !isRecurring || scope === "series"
              ? ruleFromRepeat(repeat)
              : null,
          status,
        },
        event,
        isRecurring ? scope : null,
      );
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "The event could not be saved.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (!event) return;
    const target =
      isRecurring && scope === "series" ? "complete series" : "event";
    if (!window.confirm(`Delete the ${target} “${event.title}”?`)) {
      return;
    }
    setError(null);
    setIsSaving(true);
    try {
      await onDelete(event, isRecurring ? scope : null);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "The event could not be deleted.",
      );
      setIsSaving(false);
    }
  }

  const occurrenceCalendarLocked = isRecurring && scope === "occurrence";

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        aria-labelledby="event-dialog-title"
        aria-modal="true"
        className="event-dialog"
        ref={dialogRef}
        role="dialog"
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">{event ? "Calendar event" : "New event"}</p>
            <h2 id="event-dialog-title">
              {isReadOnly
                ? "Event details"
                : event
                  ? "Edit event"
                  : "Create event"}
            </h2>
          </div>
          <button
            aria-label="Close event dialog"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <Icon name="x" size={19} />
          </button>
        </header>

        {isReadOnly && (
          <div className="read-only-notice">
            <Icon name="lock" size={17} />
            <span>
              This event belongs to a read-only calendar and cannot be changed.
            </span>
          </div>
        )}

        {!isReadOnly && isRecurring && (
          <fieldset className="recurrence-scope">
            <legend>Apply changes to</legend>
            <label>
              <input
                checked={scope === "occurrence"}
                name="recurrence-scope"
                onChange={() => handleScopeChange("occurrence")}
                type="radio"
              />
              This occurrence
            </label>
            <label>
              <input
                checked={scope === "series"}
                name="recurrence-scope"
                onChange={() => handleScopeChange("series")}
                type="radio"
              />
              Complete series
            </label>
          </fieldset>
        )}

        <form className="event-form" onSubmit={handleSubmit}>
          <label className="field field-wide">
            <span>Title</span>
            <input
              data-dialog-autofocus={!event ? "true" : undefined}
              disabled={isReadOnly}
              maxLength={240}
              onChange={(input) => setTitle(input.target.value)}
              placeholder="What is happening?"
              required
              value={title}
            />
          </label>

          <label className="field field-wide">
            <span>Calendar</span>
            <select
              disabled={isReadOnly || occurrenceCalendarLocked}
              onChange={(input) => setCalendarId(input.target.value)}
              required
              value={calendarId}
            >
              {isReadOnly && eventCalendar && (
                <option value={eventCalendar.id}>{eventCalendar.name}</option>
              )}
              {writableCalendars.map((calendar) => (
                <option key={calendar.id} value={calendar.id}>
                  {calendar.name}
                </option>
              ))}
            </select>
          </label>

          <label className="check-field field-wide all-day-field">
            <input
              checked={allDay}
              disabled={isReadOnly}
              onChange={(input) => handleAllDayChange(input.target.checked)}
              type="checkbox"
            />
            All-day event
          </label>

          <label className="field">
            <span>Starts</span>
            <input
              disabled={isReadOnly}
              onChange={(input) => setStartAt(input.target.value)}
              required
              type={allDay ? "date" : "datetime-local"}
              value={startAt}
            />
          </label>

          <label className="field">
            <span>{allDay ? "Ends (exclusive)" : "Ends"}</span>
            <input
              disabled={isReadOnly}
              onChange={(input) => setEndAt(input.target.value)}
              required
              type={allDay ? "date" : "datetime-local"}
              value={endAt}
            />
          </label>

          {(!isRecurring || scope === "series") && (
            <label className="field field-wide">
              <span>Repeats</span>
              <select
                disabled={isReadOnly}
                onChange={(input) =>
                  setRepeat(input.target.value as RepeatOption)
                }
                value={repeat}
              >
                <option value="none">Does not repeat</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </label>
          )}

          {isRecurring && scope === "occurrence" && (
            <p className="timezone-note field-wide">
              <Icon name="refresh" size={15} />
              {recurrenceLabel(
                seriesEvent?.recurrence_rule ?? event?.recurrence_rule ?? null,
              )}
              {" series · this occurrence remains on the same calendar"}
            </p>
          )}

          <label className="field field-wide">
            <span>
              <Icon name="location" size={15} /> Location
            </span>
            <input
              disabled={isReadOnly}
              maxLength={500}
              onChange={(input) => setLocation(input.target.value)}
              placeholder="Add a location"
              value={location}
            />
          </label>

          <label className="field field-wide">
            <span>Description</span>
            <textarea
              disabled={isReadOnly}
              onChange={(input) => setDescription(input.target.value)}
              placeholder="Add notes or context"
              rows={3}
              value={description}
            />
          </label>

          <label className="field field-wide">
            <span>Status</span>
            <select
              disabled={isReadOnly}
              onChange={(input) => setStatus(input.target.value as EventStatus)}
              value={status}
            >
              <option value="confirmed">Confirmed</option>
              <option value="tentative">Tentative</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </label>

          <div className="timezone-note field-wide">
            <Icon name="clock" size={15} /> Times are stored safely and shown in
            your local time.
          </div>

          {error && (
            <p className="form-error field-wide" role="alert">
              {error}
            </p>
          )}

          <footer className="dialog-footer field-wide">
            {event && !isReadOnly ? (
              <button
                className="danger-button"
                disabled={isSaving}
                onClick={handleDelete}
                type="button"
              >
                <Icon name="trash" size={17} />
                {isRecurring && scope === "series" ? "Delete series" : "Delete"}
              </button>
            ) : (
              <span />
            )}
            <div>
              <button
                className="quiet-button"
                disabled={isSaving}
                onClick={onClose}
                type="button"
              >
                Close
              </button>
              {!isReadOnly && (
                <button
                  className="primary-button"
                  disabled={isSaving}
                  type="submit"
                >
                  {isSaving
                    ? "Saving…"
                    : event
                      ? "Save changes"
                      : "Create event"}
                </button>
              )}
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}
