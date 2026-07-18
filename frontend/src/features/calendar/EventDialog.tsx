import { useState, type FormEvent } from "react";

import { Icon } from "../../components/Icon";
import { defaultEventWindow, toDateTimeLocal } from "./dateUtils";
import type {
  CalendarEvent,
  CalendarModel,
  EventMutation,
  EventStatus,
} from "./types";

interface EventDialogProps {
  calendars: CalendarModel[];
  draftDay: Date;
  event: CalendarEvent | null;
  onClose: () => void;
  onDelete: (event: CalendarEvent) => Promise<void>;
  onSave: (
    payload: EventMutation,
    event: CalendarEvent | null,
  ) => Promise<void>;
}

export function EventDialog({
  calendars,
  draftDay,
  event,
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
  const [defaultStart, defaultEnd] = defaultEventWindow(draftDay);
  const [calendarId, setCalendarId] = useState(
    event?.calendar_id ?? writableCalendars[0]?.id ?? "",
  );
  const [title, setTitle] = useState(event?.title ?? "");
  const [description, setDescription] = useState(event?.description ?? "");
  const [location, setLocation] = useState(event?.location ?? "");
  const [startAt, setStartAt] = useState(
    toDateTimeLocal(event?.start_at ?? defaultStart),
  );
  const [endAt, setEndAt] = useState(
    toDateTimeLocal(event?.end_at ?? defaultEnd),
  );
  const [status, setStatus] = useState<EventStatus>(
    event?.status ?? "confirmed",
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

    const start = new Date(startAt);
    const end = new Date(endAt);
    if (
      Number.isNaN(start.getTime()) ||
      Number.isNaN(end.getTime()) ||
      end <= start
    ) {
      setError("The end time must be later than the start time.");
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
          timezone: "Europe/Stockholm",
          status,
        },
        event,
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
    if (!event || !window.confirm(`Delete “${event.title}”?`)) {
      return;
    }
    setError(null);
    setIsSaving(true);
    try {
      await onDelete(event);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "The event could not be deleted.",
      );
      setIsSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        aria-labelledby="event-dialog-title"
        aria-modal="true"
        className="event-dialog"
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

        <form className="event-form" onSubmit={handleSubmit}>
          <label className="field field-wide">
            <span>Title</span>
            <input
              autoFocus={!event}
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
              disabled={isReadOnly}
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

          <label className="field">
            <span>Starts</span>
            <input
              disabled={isReadOnly}
              onChange={(input) => setStartAt(input.target.value)}
              required
              type="datetime-local"
              value={startAt}
            />
          </label>

          <label className="field">
            <span>Ends</span>
            <input
              disabled={isReadOnly}
              onChange={(input) => setEndAt(input.target.value)}
              required
              type="datetime-local"
              value={endAt}
            />
          </label>

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
                <Icon name="trash" size={17} /> Delete
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
