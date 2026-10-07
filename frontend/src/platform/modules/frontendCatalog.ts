import { assistantModuleEntry } from "../../features/assistant/entry";
import { calendarModuleEntry } from "../../features/calendar/entry";
import { coursesModuleEntry } from "../../features/courses/entry";
import { documentsModuleEntry } from "../../features/documents/entry";
import { inboxModuleEntry } from "../../features/inbox/entry";
import { platformModuleEntry } from "../entry";
import { moduleCatalog } from "./catalog";
import type { ModuleId, PageId } from "./contract";
import {
  assembleFrontendPages,
  assembleFrontendSettingsPanels,
  type FrontendModuleEntry,
} from "./frontendContract";

export const frontendModuleEntries = [
  platformModuleEntry,
  calendarModuleEntry,
  coursesModuleEntry,
  inboxModuleEntry,
  documentsModuleEntry,
  assistantModuleEntry,
] as const satisfies readonly FrontendModuleEntry<ModuleId, PageId>[];

export const registeredPages = assembleFrontendPages<ModuleId, PageId>(
  moduleCatalog,
  frontendModuleEntries,
);

export const registeredSettingsPanels = assembleFrontendSettingsPanels(
  moduleCatalog,
  frontendModuleEntries,
);
