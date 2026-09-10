import { Icon } from "../../platform/ui";
import type {
  CalendarModel,
  DisplayCalendarEvent,
  EventFilters,
} from "./types";

interface CalendarFiltersProps {
  calendars: CalendarModel[];
  filters: EventFilters;
  results: DisplayCalendarEvent[];
  onChange: (filters: EventFilters) => void;
  onSelectEvent: (event: DisplayCalendarEvent) => void;
}

function hasFilters(filters: EventFilters) {
  return Boolean(
    filters.search || filters.calendarId || filters.dateFrom || filters.dateTo,
  );
}

export function CalendarFilters({
  calendars,
  filters,
  results,
  onChange,
  onSelectEvent,
}: CalendarFiltersProps) {
  const active = hasFilters(filters);

  function update<Key extends keyof EventFilters>(
    key: Key,
    value: EventFilters[Key],
  ) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <section className="calendar-filter-panel" aria-label="Search and filters">
      <div className="calendar-filter-controls">
        <label className="search-field">
          <span className="sr-only">Search events</span>
          <Icon name="calendar" size={15} />
          <input
            onChange={(input) => update("search", input.target.value)}
            placeholder="Search title, description, or location"
            type="search"
            value={filters.search}
          />
        </label>
        <label className="compact-filter-field">
          <span>Calendar</span>
          <select
            aria-label="Filter by calendar"
            onChange={(input) => update("calendarId", input.target.value)}
            value={filters.calendarId}
          >
            <option value="">All calendars</option>
            {calendars.map((calendar) => (
              <option key={calendar.id} value={calendar.id}>
                {calendar.name}
              </option>
            ))}
          </select>
        </label>
        <label className="compact-filter-field date-filter-field">
          <span>From</span>
          <input
            aria-label="Events from date"
            onChange={(input) => update("dateFrom", input.target.value)}
            type="date"
            value={filters.dateFrom}
          />
        </label>
        <label className="compact-filter-field date-filter-field">
          <span>To</span>
          <input
            aria-label="Events through date"
            min={filters.dateFrom || undefined}
            onChange={(input) => update("dateTo", input.target.value)}
            type="date"
            value={filters.dateTo}
          />
        </label>
        {active && (
          <button
            className="quiet-button clear-filter-button"
            onClick={() =>
              onChange({ search: "", calendarId: "", dateFrom: "", dateTo: "" })
            }
            type="button"
          >
            Clear
          </button>
        )}
      </div>

      {active && (
        <div className="calendar-search-results" aria-live="polite">
          <strong>
            {results.length} {results.length === 1 ? "event" : "events"}
          </strong>
          <div>
            {results.slice(0, 8).map((event) => (
              <button
                key={event.display_id}
                onClick={() => onSelectEvent(event)}
                type="button"
              >
                <span>{event.title}</span>
                <small>
                  {new Date(event.start_at).toLocaleDateString("en", {
                    month: "short",
                    day: "numeric",
                  })}
                </small>
              </button>
            ))}
            {results.length > 8 && <span>+{results.length - 8} more</span>}
            {results.length === 0 && (
              <span>No matching events in this date range.</span>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
