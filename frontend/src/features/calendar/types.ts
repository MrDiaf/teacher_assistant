export type CalendarSourceType = "local" | "ics_import";
export type EventStatus = "confirmed" | "tentative" | "cancelled";
export type CalendarView = "month" | "week" | "day";

export interface CalendarModel {
  id: string;
  name: string;
  description: string | null;
  color: string;
  is_visible: boolean;
  is_read_only: boolean;
  source_type: CalendarSourceType;
  created_at: string;
  updated_at: string;
}

export interface CalendarEvent {
  id: string;
  calendar_id: string;
  title: string;
  description: string | null;
  location: string | null;
  start_at: string;
  end_at: string;
  all_day: boolean;
  timezone: string;
  recurrence_rule: string | null;
  recurrence_parent_id: string | null;
  status: EventStatus;
  created_at: string;
  updated_at: string;
}

export interface EventMutation {
  calendar_id: string;
  title: string;
  description: string | null;
  location: string | null;
  start_at: string;
  end_at: string;
  timezone: string;
  status: EventStatus;
}
