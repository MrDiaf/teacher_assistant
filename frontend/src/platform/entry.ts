import { SettingsPage } from "../features/settings/SettingsPage";
import "../features/ai/styles.css";
import type { FrontendModuleEntry } from "./modules/frontendContract";
import { DashboardPage, StudyPlanPage } from "./pages/PlaceholderPages";

export const platformModuleEntry = {
  id: "platform",
  pages: [
    { id: "dashboard", icon: "dashboard", component: DashboardPage },
    { id: "study-plan", icon: "checklist", component: StudyPlanPage },
    { id: "settings", icon: "settings", component: SettingsPage },
  ],
} as const satisfies FrontendModuleEntry;
