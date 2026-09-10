import { useState, type FormEvent } from "react";

import { Icon, useModalDialog } from "../../platform/ui";
import type { CalendarModel, CalendarMutation } from "./types";

const DEFAULT_COLOR = "#29584c";

interface CalendarDialogProps {
  calendar: CalendarModel | null;
  onClose: () => void;
  onDelete: (calendar: CalendarModel) => Promise<void>;
  onSave: (
    payload: CalendarMutation | Partial<CalendarMutation>,
    calendar: CalendarModel | null,
  ) => Promise<void>;
}

export function CalendarDialog({
  calendar,
  onClose,
  onDelete,
  onSave,
}: CalendarDialogProps) {
  const isExistingReadOnly = Boolean(calendar?.is_read_only);
  const isImported = calendar?.source_type === "ics_import";
  const [name, setName] = useState(calendar?.name ?? "");
  const [description, setDescription] = useState(calendar?.description ?? "");
  const [color, setColor] = useState(calendar?.color ?? DEFAULT_COLOR);
  const [isVisible, setIsVisible] = useState(calendar?.is_visible ?? true);
  const [isReadOnly, setIsReadOnly] = useState(calendar?.is_read_only ?? false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useModalDialog(onClose);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Add a name for the calendar.");
      return;
    }
    setIsSaving(true);
    try {
      const payload = isExistingReadOnly
        ? { is_visible: isVisible, is_read_only: isReadOnly }
        : {
            name: name.trim(),
            description: description.trim() || null,
            color,
            is_visible: isVisible,
            is_read_only: isReadOnly,
          };
      await onSave(payload, calendar);
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "The calendar could not be saved.",
      );
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (
      !calendar ||
      !window.confirm(
        `Delete “${calendar.name}” and all of its events? This cannot be undone.`,
      )
    ) {
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await onDelete(calendar);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "The calendar could not be deleted.",
      );
      setIsSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        aria-labelledby="calendar-dialog-title"
        aria-modal="true"
        className="event-dialog calendar-dialog"
        ref={dialogRef}
        role="dialog"
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">
              {calendar ? "Calendar settings" : "New calendar"}
            </p>
            <h2 id="calendar-dialog-title">
              {calendar ? "Manage calendar" : "Create calendar"}
            </h2>
          </div>
          <button
            aria-label="Close calendar dialog"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <Icon name="x" size={19} />
          </button>
        </header>

        {isExistingReadOnly && (
          <div className="read-only-notice">
            <Icon name="lock" size={17} />
            <span>
              {isImported
                ? "Imported calendar details are protected; visibility can still be changed."
                : "Unlock this local calendar before changing its name, description, or color."}
            </span>
          </div>
        )}

        <form className="event-form" onSubmit={handleSubmit}>
          <label className="field field-wide">
            <span>Name</span>
            <input
              data-dialog-autofocus={!calendar ? "true" : undefined}
              disabled={isExistingReadOnly}
              maxLength={120}
              onChange={(input) => setName(input.target.value)}
              required
              value={name}
            />
          </label>

          <label className="field field-wide">
            <span>Description</span>
            <textarea
              disabled={isExistingReadOnly}
              onChange={(input) => setDescription(input.target.value)}
              placeholder="What belongs on this calendar?"
              rows={3}
              value={description}
            />
          </label>

          <label className="field">
            <span>Color</span>
            <input
              aria-label="Calendar color"
              disabled={isExistingReadOnly}
              onChange={(input) => setColor(input.target.value)}
              type="color"
              value={color}
            />
          </label>

          <div className="field calendar-protection-options">
            <span>Options</span>
            <label className="check-field">
              <input
                checked={isVisible}
                onChange={(input) => setIsVisible(input.target.checked)}
                type="checkbox"
              />
              Show this calendar
            </label>
            <label className="check-field">
              <input
                checked={isReadOnly}
                disabled={isImported}
                onChange={(input) => setIsReadOnly(input.target.checked)}
                type="checkbox"
              />
              Protect as read-only
            </label>
          </div>

          {isImported && (
            <p className="timezone-note field-wide">
              <Icon name="lock" size={15} /> Imported calendars remain read-only
              and cannot be deleted.
            </p>
          )}

          {error && (
            <p className="form-error field-wide" role="alert">
              {error}
            </p>
          )}

          <footer className="dialog-footer field-wide">
            {calendar && !calendar.is_read_only && !isImported ? (
              <button
                className="danger-button"
                disabled={isSaving}
                onClick={handleDelete}
                type="button"
              >
                <Icon name="trash" size={17} /> Delete calendar
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
              <button
                className="primary-button"
                disabled={isSaving}
                type="submit"
              >
                {isSaving
                  ? "Saving…"
                  : calendar
                    ? isExistingReadOnly && !isReadOnly
                      ? "Unlock calendar"
                      : "Save changes"
                    : "Create calendar"}
              </button>
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}
