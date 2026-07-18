import { useState, type ChangeEvent } from "react";

import { Icon } from "../../components/Icon";
import { calendarApi } from "./api";
import { recurrenceLabel } from "./recurrence";
import type { CalendarModel, IcsImportResult, IcsPreview } from "./types";

const MAX_FILE_SIZE = 5 * 1024 * 1024;

interface IcsImportDialogProps {
  calendars: CalendarModel[];
  onClose: () => void;
  onImported: () => void;
}

function eventDate(startAt: string | null, allDay: boolean): string {
  if (!startAt) return "Date unavailable";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    ...(allDay ? {} : { timeStyle: "short" }),
  }).format(new Date(startAt));
}

export function IcsImportDialog({
  calendars,
  onClose,
  onImported,
}: IcsImportDialogProps) {
  const writableCalendars = calendars.filter(
    (calendar) => !calendar.is_read_only,
  );
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<"upload" | "subscribe">("upload");
  const [subscriptionUrl, setSubscriptionUrl] = useState("");
  const [preview, setPreview] = useState<IcsPreview | null>(null);
  const [destination, setDestination] = useState("new");
  const [calendarName, setCalendarName] = useState("Imported calendar");
  const [calendarColor, setCalendarColor] = useState("#5b7fa3");
  const [result, setResult] = useState<IcsImportResult | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function changeMode(nextMode: "upload" | "subscribe") {
    setMode(nextMode);
    setPreview(null);
    setResult(null);
    setError(null);
    setDestination("new");
  }

  async function handleFileChange(changeEvent: ChangeEvent<HTMLInputElement>) {
    const selected = changeEvent.target.files?.[0] ?? null;
    setFile(selected);
    setPreview(null);
    setResult(null);
    setError(null);
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith(".ics")) {
      setError("Choose a file with the .ics extension.");
      return;
    }
    if (selected.size > MAX_FILE_SIZE) {
      setError("The ICS file exceeds the 5 MB upload limit.");
      return;
    }
    setIsPreviewing(true);
    try {
      const loadedPreview = await calendarApi.previewIcs(selected);
      setPreview(loadedPreview);
      setCalendarName(loadedPreview.suggested_calendar_name);
    } catch (previewError) {
      setError(
        previewError instanceof Error
          ? previewError.message
          : "The ICS file could not be previewed.",
      );
    } finally {
      setIsPreviewing(false);
    }
  }

  async function handleSubscriptionPreview() {
    const url = subscriptionUrl.trim();
    if (!url) {
      setError("Enter the public URL of an ICS calendar.");
      return;
    }
    setIsPreviewing(true);
    setPreview(null);
    setResult(null);
    setError(null);
    try {
      const loadedPreview = await calendarApi.previewIcsSubscription(url);
      setPreview(loadedPreview);
      setCalendarName(loadedPreview.suggested_calendar_name);
    } catch (previewError) {
      setError(
        previewError instanceof Error
          ? previewError.message
          : "The subscribed calendar could not be previewed.",
      );
    } finally {
      setIsPreviewing(false);
    }
  }

  async function handleImport() {
    if (!preview || preview.importable_events === 0) return;
    if (mode === "upload" && !file) return;
    if (destination === "new" && !calendarName.trim()) {
      setError("Add a name for the imported calendar.");
      return;
    }
    setIsImporting(true);
    setError(null);
    try {
      const importResult =
        mode === "subscribe"
          ? await calendarApi.createIcsSubscription({
              url: subscriptionUrl.trim(),
              calendarName: calendarName.trim(),
              calendarColor,
            })
          : await calendarApi.importIcs(file!, {
              destinationCalendarId: destination === "new" ? "" : destination,
              calendarName: calendarName.trim(),
              calendarColor,
            });
      setResult(importResult);
      onImported();
    } catch (importError) {
      setError(
        importError instanceof Error
          ? importError.message
          : "The ICS events could not be imported.",
      );
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        aria-labelledby="ics-import-title"
        aria-modal="true"
        className="event-dialog ics-import-dialog"
        role="dialog"
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">Calendar data</p>
            <h2 id="ics-import-title">Add an ICS calendar</h2>
          </div>
          <button
            aria-label="Close ICS import dialog"
            className="icon-button"
            disabled={isImporting}
            onClick={onClose}
            type="button"
          >
            <Icon name="x" size={19} />
          </button>
        </header>

        <div className="ics-import-content">
          {result ? (
            <div className="import-result" role="status">
              <span className="empty-symbol large">
                <Icon name="checklist" size={27} />
              </span>
              <p className="eyebrow">
                {mode === "subscribe"
                  ? "Subscription added"
                  : "Import complete"}
              </p>
              <h3>{result.calendar.name}</h3>
              <p>
                Imported {result.imported_count}{" "}
                {result.imported_count === 1 ? "event" : "events"}.
                {result.duplicate_count > 0 &&
                  ` Skipped ${result.duplicate_count} duplicate ${
                    result.duplicate_count === 1 ? "UID" : "UIDs"
                  }.`}
                {result.skipped_count > 0 &&
                  ` ${result.skipped_count} unsupported ${
                    result.skipped_count === 1 ? "entry was" : "entries were"
                  } not imported.`}
              </p>
              <div className="import-protection-summary">
                <Icon
                  name={result.calendar.is_read_only ? "lock" : "calendar"}
                  size={16}
                />
                <span>
                  {result.calendar.is_subscribed
                    ? "This calendar is read-only and refreshes from its source daily."
                    : result.calendar.is_read_only
                      ? "The new imported calendar is read-only."
                      : "Events were copied into your writable local calendar."}
                </span>
              </div>
              {result.errors.length > 0 && (
                <ul className="import-result-errors">
                  {result.errors.map((problem) => (
                    <li key={`${problem.index}:${problem.uid}`}>
                      Event {problem.index}: {problem.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <>
              <div
                className="ics-source-tabs"
                role="tablist"
                aria-label="ICS source"
              >
                <button
                  aria-selected={mode === "upload"}
                  className={mode === "upload" ? "active" : ""}
                  onClick={() => changeMode("upload")}
                  role="tab"
                  type="button"
                >
                  Upload file
                </button>
                <button
                  aria-selected={mode === "subscribe"}
                  className={mode === "subscribe" ? "active" : ""}
                  onClick={() => changeMode("subscribe")}
                  role="tab"
                  type="button"
                >
                  Subscribe by URL
                </button>
              </div>

              {mode === "upload" ? (
                <label className="ics-file-drop">
                  <Icon name="calendar" size={24} />
                  <span>
                    <strong>{file ? file.name : "Choose an .ics file"}</strong>
                    <small>UTF-8 · up to 5 MB · previewed before import</small>
                  </span>
                  <input
                    accept=".ics,text/calendar"
                    aria-label="ICS file"
                    disabled={isPreviewing || isImporting}
                    onChange={handleFileChange}
                    type="file"
                  />
                </label>
              ) : (
                <div className="ics-subscription-source">
                  <label className="field field-wide">
                    <span>Public ICS URL</span>
                    <input
                      aria-label="ICS subscription URL"
                      disabled={isPreviewing || isImporting}
                      onChange={(input) => {
                        setSubscriptionUrl(input.target.value);
                        setPreview(null);
                        setResult(null);
                      }}
                      placeholder="https://example.com/calendar.ics"
                      type="url"
                      value={subscriptionUrl}
                    />
                  </label>
                  <button
                    className="quiet-button"
                    disabled={
                      isPreviewing || isImporting || !subscriptionUrl.trim()
                    }
                    onClick={handleSubscriptionPreview}
                    type="button"
                  >
                    Preview subscription
                  </button>
                  <p>
                    The address stays private on this installation. Local and
                    private-network addresses are blocked for safety.
                  </p>
                </div>
              )}

              {isPreviewing && (
                <div className="import-loading" role="status">
                  <span /> Reading and validating calendar events…
                </div>
              )}

              {preview && (
                <>
                  <div className="import-preview-summary">
                    <div>
                      <strong>{preview.total_events}</strong>
                      <span>Total entries</span>
                    </div>
                    <div>
                      <strong>{preview.importable_events}</strong>
                      <span>Ready to import</span>
                    </div>
                    <div className={preview.skipped_events ? "has-errors" : ""}>
                      <strong>{preview.skipped_events}</strong>
                      <span>Unsupported</span>
                    </div>
                  </div>

                  <div className="import-destination">
                    <label className="field field-wide">
                      <span>Destination</span>
                      <select
                        aria-label="Import destination"
                        disabled={mode === "subscribe"}
                        onChange={(input) => setDestination(input.target.value)}
                        value={destination}
                      >
                        <option value="new">
                          Create a protected imported calendar
                        </option>
                        {mode === "upload" &&
                          writableCalendars.map((calendar) => (
                            <option key={calendar.id} value={calendar.id}>
                              Copy into {calendar.name} (writable)
                            </option>
                          ))}
                      </select>
                    </label>
                    {destination === "new" && (
                      <>
                        <label className="field">
                          <span>Calendar name</span>
                          <input
                            aria-label="Imported calendar name"
                            maxLength={120}
                            onChange={(input) =>
                              setCalendarName(input.target.value)
                            }
                            value={calendarName}
                          />
                        </label>
                        <label className="field">
                          <span>Color</span>
                          <input
                            aria-label="Imported calendar color"
                            onChange={(input) =>
                              setCalendarColor(input.target.value)
                            }
                            type="color"
                            value={calendarColor}
                          />
                        </label>
                      </>
                    )}
                    <div className="import-destination-note field-wide">
                      <Icon
                        name={destination === "new" ? "lock" : "calendar"}
                        size={15}
                      />
                      <span>
                        {mode === "subscribe"
                          ? "Subscriptions are locked read-only and refreshed from their source every day."
                          : destination === "new"
                            ? "New imported calendars are locked read-only after their initial import."
                            : "Imported events remain editable in the selected local calendar. UIDs still prevent duplicates."}
                      </span>
                    </div>
                  </div>

                  <div className="import-event-preview">
                    <div className="import-event-preview-heading">
                      <strong>Event preview</strong>
                      <span>UIDs are preserved where supplied.</span>
                    </div>
                    <div className="import-event-list">
                      {preview.events.slice(0, 50).map((event) => (
                        <article
                          className={event.is_importable ? "" : "unsupported"}
                          key={`${event.index}:${event.uid}`}
                        >
                          <span className="import-event-status">
                            {event.is_importable ? "Ready" : "Skip"}
                          </span>
                          <div>
                            <strong>{event.title}</strong>
                            <small>
                              {eventDate(event.start_at, event.all_day)}
                              {event.all_day
                                ? " · All day"
                                : ` · ${event.timezone}`}
                              {event.recurrence_rule
                                ? ` · ${recurrenceLabel(event.recurrence_rule)}`
                                : ""}
                            </small>
                            {event.issues.map((issue) => (
                              <span
                                className={`import-issue ${issue.severity}`}
                                key={`${issue.severity}:${issue.message}`}
                              >
                                {issue.message}
                              </span>
                            ))}
                          </div>
                        </article>
                      ))}
                      {preview.events.length > 50 && (
                        <p className="import-list-overflow">
                          +{preview.events.length - 50} additional entries will
                          be processed.
                        </p>
                      )}
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
        </div>

        <footer className="dialog-footer ics-import-footer">
          <span />
          <div>
            <button
              className="quiet-button"
              disabled={isImporting}
              onClick={onClose}
              type="button"
            >
              {result ? "Done" : "Close"}
            </button>
            {!result && preview && (
              <button
                className="primary-button"
                disabled={isImporting || preview.importable_events === 0}
                onClick={handleImport}
                type="button"
              >
                {isImporting
                  ? mode === "subscribe"
                    ? "Subscribing…"
                    : "Importing…"
                  : `${mode === "subscribe" ? "Subscribe to" : "Import"} ${preview.importable_events} ${
                      preview.importable_events === 1 ? "event" : "events"
                    }`}
              </button>
            )}
          </div>
        </footer>
      </section>
    </div>
  );
}
