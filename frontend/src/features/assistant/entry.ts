import type { FrontendModuleEntry } from "../../platform/modules/frontendContract";
import { AssistantPage } from "./AssistantPage";
import "./styles.css";

export const assistantModuleEntry = {
  id: "assistant",
  pages: [{ id: "assistant", icon: "assistant", component: AssistantPage }],
  settingsPanels: [],
} as const satisfies FrontendModuleEntry;
