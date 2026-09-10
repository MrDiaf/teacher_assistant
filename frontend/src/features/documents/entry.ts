import type { FrontendModuleEntry } from "../../platform/modules/frontendContract";
import { DocumentsPage } from "./DocumentsPage";

export const documentsModuleEntry = {
  id: "documents",
  pages: [{ id: "documents", icon: "file", component: DocumentsPage }],
} as const satisfies FrontendModuleEntry;
