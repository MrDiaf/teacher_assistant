import { Icon } from "../../components/Icon";
import type { CalendarModel } from "./types";

interface CalendarListProps {
  calendars: CalendarModel[];
  isBootstrapping: boolean;
  isLoading: boolean;
  onBootstrap: () => void;
  onVisibilityChange: (calendar: CalendarModel, visible: boolean) => void;
}

export function CalendarList({
  calendars,
  isBootstrapping,
  isLoading,
  onBootstrap,
  onVisibilityChange,
}: CalendarListProps) {
  return (
    <aside className="calendar-list-panel" aria-label="Calendars">
      <div className="calendar-list-heading">
        <div>
          <p className="eyebrow">Calendars</p>
          <h2>My calendars</h2>
        </div>
        <span className="calendar-count">{calendars.length}</span>
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
            <label className="calendar-option" key={calendar.id}>
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
                  {calendar.source_type === "local" ? "Local" : "Imported"}
                </small>
              </span>
              {calendar.is_read_only && (
                <span className="read-only-icon" title="Read-only calendar">
                  <Icon name="lock" size={14} />
                </span>
              )}
            </label>
          ))}
        </div>
      )}

      <div className="calendar-list-note">
        <Icon name="lock" size={15} />
        <span>Read-only calendars stay visible but protected.</span>
      </div>
    </aside>
  );
}
