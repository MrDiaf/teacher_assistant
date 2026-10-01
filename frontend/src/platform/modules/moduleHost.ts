import { assistantModuleEntry } from "../../features/assistant/entry";
import { calendarModuleEntry } from "../../features/calendar/entry";
import { coursesModuleEntry } from "../../features/courses/entry";
import { documentsModuleEntry } from "../../features/documents/entry";
import { platformModuleEntry } from "../entry";
import { moduleCatalog } from "./catalog";
import { selectModuleCatalog, type ModuleId, type PageId } from "./contract";
import {
  assembleFrontendPages,
  type FrontendModuleEntry,
  type RegisteredPage,
} from "./frontendContract";

export const SUPPORTED_MODULE_HOST_IDS = [
  "assistant",
  "calendar",
  "courses",
  "documents",
] as const;
export type ModuleHostId = (typeof SUPPORTED_MODULE_HOST_IDS)[number];

const moduleHostEntries = [
  platformModuleEntry,
  assistantModuleEntry,
  calendarModuleEntry,
  coursesModuleEntry,
  documentsModuleEntry,
] as const satisfies readonly FrontendModuleEntry<ModuleId, PageId>[];

export function assembleModuleHostPages(
  moduleId: string,
): readonly RegisteredPage<PageId>[] {
  if (!SUPPORTED_MODULE_HOST_IDS.includes(moduleId as ModuleHostId)) {
    throw new Error(
      `Unsupported module host ${JSON.stringify(moduleId)}; supported modules: ${SUPPORTED_MODULE_HOST_IDS.join(", ")}`,
    );
  }
  const selectedCatalog = selectModuleCatalog(moduleCatalog, [moduleId]);
  const selectedIds = new Set(
    selectedCatalog.registrations.map((registration) => registration.id),
  );
  const pages = assembleFrontendPages<ModuleId, PageId>(
    selectedCatalog,
    moduleHostEntries.filter((entry) => selectedIds.has(entry.id)),
  ).filter((page) => page.moduleId === moduleId);
  if (pages.length === 0) {
    throw new Error(`Module host ${JSON.stringify(moduleId)} has no page`);
  }
  return Object.freeze(pages);
}
