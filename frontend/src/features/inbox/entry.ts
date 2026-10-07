import type { FrontendModuleEntry } from "../../platform/modules/frontendContract";
import { InboxPage } from "./InboxPage";
import { MailInboxSettingsPanel } from "./MailInboxSettingsPanel";
import "./styles.css";

export const inboxModuleEntry = {
  id: "inbox",
  pages: [{ id: "inbox", icon: "inbox", component: InboxPage }],
  settingsPanels: [{ id: "mail-inbox", component: MailInboxSettingsPanel }],
} as const satisfies FrontendModuleEntry;
