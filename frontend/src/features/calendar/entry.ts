import type { FrontendModuleEntry } from "../../platform/modules/frontendContract";
import { CalendarPage } from "./CalendarPage";

export const calendarModuleEntry = {
  id: "calendar",
  pages: [{ id: "calendar", icon: "calendar", component: CalendarPage }],
} as const satisfies FrontendModuleEntry;
