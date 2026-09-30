/** Typed Calendar surface available to declared feature consumers. */

import { calendarApi } from "./api";

export {
  CalendarWorkspace,
  type CalendarSidebarRenderProps,
} from "./CalendarPage";
export type { CalendarEvent, CalendarModel } from "./types";

export const calendarConsumerApi = Object.freeze({
  listCalendars: calendarApi.listCalendars,
});

/**
 * Calendar class names a declared consumer may target or reuse.
 *
 * A feature that embeds `CalendarWorkspace`, or renders its own panel beside
 * it, styles against these names only. They are part of this contract: Calendar
 * keeps each one defined in its stylesheet, and a consumer must not reach for
 * any other Calendar class. `protected` and `large` are modifiers of
 * `calendar-option` and `empty-symbol`. `event-dialog` and `event-form` are the dialog shell
 * that existing feature dialogs already share.
 */
export const calendarEmbeddingClasses = Object.freeze([
  "embedded-calendar-page",
  "calendar-toolbar",
  "calendar-title-block",
  "calendar-workspace",
  "calendar-view-frame",
  "calendar-list-panel",
  "calendar-list-heading",
  "calendar-list-skeleton",
  "calendar-list-note",
  "calendar-count",
  "calendar-options",
  "calendar-option",
  "calendar-option-copy",
  "protected",
  "calendar-color",
  "read-only-icon",
  "main-empty-state",
  "empty-symbol",
  "large",
  "event-dialog",
  "event-form",
] as const);
