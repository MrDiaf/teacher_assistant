import { Icon } from "../../components/Icon";
import type { CalendarModel } from "./types";

interface CalendarListProps {
  calendars: CalendarModel[];
  isBootstrapping: boolean;
  isLoading: boolean;
  onBootstrap: () => void;
  onCreate: () => void;
  onImport: () => void;
  onManage: (calendar: CalendarModel) => void;
  onVisibilityChange: (calendar: CalendarModel, visible: boolean) => void;
}

export function CalendarList({
  calendars,
  isBootstrapping,
  isLoading,
  onBootstrap,
  onCreate,
  onImport,
  onManage,
  onVisibilityChange,
}: CalendarListProps) {
  return (
    <aside className="calendar-list-panel" aria-label="Calendars">
      <div className="calendar-list-heading">
        <div>
          <p className="eyebrow">Calendars</p>
          <h2>My calendars</h2>
        </div>
        <div className="calendar-list-heading-actions">
          <span className="calendar-count">{calendars.length}</span>
          <button
            aria-label="Create calendar"
            className="calendar-add-button"
            onClick={onCreate}
            type="button"
          >
            <Icon name="plus" size={15} />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="calendar-list-skeleton" aria-label="Loading calendars">
          <span />
          <span />
          <span />
        </div>
      ) : calendars.length === 0 ? (
        <div className="calendar-list-empty">
          <span className="empty-symbol">
            <Icon name="calendar" size={21} />
          </span>
          <strong>No calendar yet</strong>
          <p>Set up a Personal calendar to start adding events.</p>
          <button
            className="text-button"
            disabled={isBootstrapping}
            onClick={onBootstrap}
            type="button"
          >
            {isBootstrapping ? "Setting up…" : "Set up Personal calendar"}
          </button>
        </div>
      ) : (
        <div className="calendar-options">
          {calendars.map((calendar) => (
            <div
              className={`calendar-option${calendar.is_read_only ? " protected" : ""}`}
              key={calendar.id}
            >
              <label>
                <input
                  aria-label={`Show ${calendar.name}`}
                  checked={calendar.is_visible}
                  onChange={(event) =>
                    onVisibilityChange(calendar, event.target.checked)
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
                    {calendar.source_type === "local"
                      ? "Local"
                      : calendar.is_subscribed
                        ? "Subscribed · Daily refresh"
                        : "Imported"}
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
                aria-label={`Manage ${calendar.name}`}
                className="calendar-manage-button"
                onClick={() => onManage(calendar)}
                type="button"
              >
                <Icon name="settings" size={15} />
              </button>
            </div>
          ))}
        </div>
      )}

      <button
        className="import-calendar-button"
        onClick={onImport}
        type="button"
      >
        <Icon name="calendar" size={16} /> Import or subscribe .ics
      </button>

      <div className="calendar-list-note">
        <Icon name="lock" size={15} />
        <span>Read-only calendars stay visible but protected.</span>
      </div>
    </aside>
  );
}
