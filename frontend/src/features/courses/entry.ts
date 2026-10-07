import type { FrontendModuleEntry } from "../../platform/modules/frontendContract";
import { CoursesPage } from "./CoursesPage";

import "./styles.css";

export const coursesModuleEntry = {
  id: "courses",
  pages: [{ id: "courses", icon: "courses", component: CoursesPage }],
  settingsPanels: [],
} as const satisfies FrontendModuleEntry;
