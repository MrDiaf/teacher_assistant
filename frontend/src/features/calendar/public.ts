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
