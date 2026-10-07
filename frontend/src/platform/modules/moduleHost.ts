import { assistantModuleEntry } from "../../features/assistant/entry";
import { calendarModuleEntry } from "../../features/calendar/entry";
import { coursesModuleEntry } from "../../features/courses/entry";
import { documentsModuleEntry } from "../../features/documents/entry";
import { inboxModuleEntry } from "../../features/inbox/entry";
import { platformModuleEntry } from "../entry";
import { moduleCatalog } from "./catalog";
import { selectModuleCatalog, type ModuleId, type PageId } from "./contract";
import {
  assembleFrontendPages,
  assembleFrontendSettingsPanels,
  type FrontendModuleEntry,
  type RegisteredPage,
  type RegisteredSettingsPanel,
} from "./frontendContract";

export const SUPPORTED_MODULE_HOST_IDS = [
  "assistant",
  "calendar",
  "courses",
  "documents",
  "inbox",
] as const;
export type ModuleHostId = (typeof SUPPORTED_MODULE_HOST_IDS)[number];

const moduleHostEntries = [
  platformModuleEntry,
  assistantModuleEntry,
  calendarModuleEntry,
  coursesModuleEntry,
  documentsModuleEntry,
  inboxModuleEntry,
] as const satisfies readonly FrontendModuleEntry<ModuleId, PageId>[];

function selectedModuleHost(moduleId: string) {
  if (!SUPPORTED_MODULE_HOST_IDS.includes(moduleId as ModuleHostId)) {
    throw new Error(
      `Unsupported module host ${JSON.stringify(moduleId)}; supported modules: ${SUPPORTED_MODULE_HOST_IDS.join(", ")}`,
    );
  }
  const catalog = selectModuleCatalog(moduleCatalog, [moduleId]);
  const selectedIds = new Set(
    catalog.registrations.map((registration) => registration.id),
  );
  return {
    catalog,
    entries: moduleHostEntries.filter((entry) => selectedIds.has(entry.id)),
  };
}

export function assembleModuleHostPages(
  moduleId: string,
): readonly RegisteredPage<PageId>[] {
  const selected = selectedModuleHost(moduleId);
  const pages = assembleFrontendPages<ModuleId, PageId>(
    selected.catalog,
    selected.entries,
  ).filter(
    (page) =>
      page.moduleId === moduleId ||
      (moduleId === "inbox" && page.id === "settings"),
  );
  if (pages.length === 0) {
    throw new Error(`Module host ${JSON.stringify(moduleId)} has no page`);
  }
  return Object.freeze(pages);
}

export function assembleModuleHostSettingsPanels(
  moduleId: string,
): readonly RegisteredSettingsPanel[] {
  const selected = selectedModuleHost(moduleId);
  return assembleFrontendSettingsPanels(
    selected.catalog,
    selected.entries,
  ).filter((panel) => panel.moduleId === moduleId);
}
