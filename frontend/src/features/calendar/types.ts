import type { PersistedCalendarView } from "../../platform/persistence";

export type CalendarSourceType = "local" | "ics_import";
export type EventStatus = "confirmed" | "tentative" | "cancelled";
export type CalendarView = PersistedCalendarView;

export interface CalendarModel {
  id: string;
  name: string;
  description: string | null;
  color: string;
  is_visible: boolean;
  is_read_only: boolean;
  source_type: CalendarSourceType;
  is_subscribed: boolean;
  subscription_last_synced_at: string | null;
  subscription_next_sync_at: string | null;
  subscription_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarEvent {
  id: string;
  calendar_id: string;
  title: string;
  description: string | null;
  location: string | null;
  external_uid: string | null;
  start_at: string;
  end_at: string;
  all_day: boolean;
  timezone: string;
  recurrence_rule: string | null;
  recurrence_parent_id: string | null;
  recurrence_original_start_at: string | null;
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
  all_day: boolean;
  timezone: string;
  recurrence_rule: string | null;
  status: EventStatus;
}

export type EventUpdateMutation = Partial<EventMutation>;
export type RecurrenceScope = "occurrence" | "series";

export interface DisplayCalendarEvent extends CalendarEvent {
  display_id: string;
  occurrence_start_at: string | null;
  series_id: string | null;
  is_virtual_occurrence: boolean;
}

export interface CalendarMutation {
  name: string;
  description: string | null;
  color: string;
  is_visible: boolean;
  is_read_only: boolean;
}

export interface EventFilters {
  search: string;
  calendarId: string;
  dateFrom: string;
  dateTo: string;
}

export interface IcsIssue {
  severity: "warning" | "error";
  message: string;
}

export interface IcsPreviewEvent {
  index: number;
  uid: string | null;
  title: string;
  start_at: string | null;
  end_at: string | null;
  all_day: boolean;
  timezone: string;
  status: EventStatus;
  recurrence_rule: string | null;
  is_importable: boolean;
  issues: IcsIssue[];
}

export interface IcsPreview {
  file_name: string;
  suggested_calendar_name: string;
  total_events: number;
  importable_events: number;
  skipped_events: number;
  events: IcsPreviewEvent[];
}

export interface IcsImportError {
  index: number;
  uid: string | null;
  message: string;
}

export interface IcsImportResult {
  calendar: CalendarModel;
  imported_count: number;
  duplicate_count: number;
  skipped_count: number;
  errors: IcsImportError[];
  imported_events: CalendarEvent[];
  destination_calendar_id: string;
}

export interface IcsImportOptions {
  destinationCalendarId: string;
  calendarName: string;
  calendarColor: string;
}

export interface IcsSubscriptionOptions {
  url: string;
  calendarName: string;
  calendarColor: string;
}
