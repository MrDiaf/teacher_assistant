import { Icon } from "../../platform/ui";
import { formatHeading } from "./dateUtils";
import type { CalendarView } from "./types";

interface CalendarToolbarProps {
  anchor: Date;
  canCreate: boolean;
  eyebrow?: string;
  headingId?: string;
  onCreate: () => void;
  onMove: (direction: -1 | 1) => void;
  onToday: () => void;
  onViewChange: (view: CalendarView) => void;
  view: CalendarView;
}

const VIEWS: CalendarView[] = ["day", "week", "month"];

export function CalendarToolbar({
  anchor,
  canCreate,
  eyebrow = "Personal schedule",
  headingId = "calendar-page-title",
  onCreate,
  onMove,
  onToday,
  onViewChange,
  view,
}: CalendarToolbarProps) {
  return (
    <header className="calendar-toolbar">
      <div className="calendar-title-block">
        <p className="eyebrow">{eyebrow}</p>
        <h1 id={headingId}>{formatHeading(anchor, view)}</h1>
      </div>

      <div className="calendar-toolbar-actions">
        <div className="date-navigation" aria-label="Calendar navigation">
          <button
            className="quiet-button today-button"
            onClick={onToday}
            type="button"
          >
            Today
          </button>
          <button
            aria-label="Previous date range"
            className="icon-button"
            onClick={() => onMove(-1)}
            type="button"
          >
            <Icon name="chevron-left" size={19} />
          </button>
          <button
            aria-label="Next date range"
            className="icon-button"
            onClick={() => onMove(1)}
            type="button"
          >
            <Icon name="chevron-right" size={19} />
          </button>
        </div>

        <div className="view-switcher" aria-label="Calendar view">
          {VIEWS.map((candidate) => (
            <button
              aria-pressed={candidate === view}
              className={candidate === view ? "active" : ""}
              key={candidate}
              onClick={() => onViewChange(candidate)}
              type="button"
            >
              {candidate[0].toUpperCase() + candidate.slice(1)}
            </button>
          ))}
        </div>

        <button
          className="primary-button create-event-button"
          disabled={!canCreate}
          onClick={onCreate}
          type="button"
        >
          <Icon name="plus" size={18} />
          Create event
        </button>
      </div>
    </header>
  );
}
