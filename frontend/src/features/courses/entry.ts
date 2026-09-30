import type { FrontendModuleEntry } from "../../platform/modules/frontendContract";
import { CoursesPage } from "./CoursesPage";

import "./styles.css";

export const coursesModuleEntry = {
  id: "courses",
  pages: [{ id: "courses", icon: "courses", component: CoursesPage }],
} as const satisfies FrontendModuleEntry;
