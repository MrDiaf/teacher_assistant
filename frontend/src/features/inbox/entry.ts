import type { FrontendModuleEntry } from "../../platform/modules/frontendContract";
import { InboxPage } from "./InboxPage";

export const inboxModuleEntry = {
  id: "inbox",
  pages: [{ id: "inbox", icon: "inbox", component: InboxPage }],
} as const satisfies FrontendModuleEntry;
