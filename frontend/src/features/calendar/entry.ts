import type { FrontendModuleEntry } from "../../platform/modules/frontendContract";
import { CalendarPage } from "./CalendarPage";

import "./styles.css";

export const calendarModuleEntry = {
  id: "calendar",
  pages: [{ id: "calendar", icon: "calendar", component: CalendarPage }],
  settingsPanels: [],
} as const satisfies FrontendModuleEntry;
