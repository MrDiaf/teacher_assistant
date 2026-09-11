import type { FrontendModuleEntry } from "../../platform/modules/frontendContract";
import { DocumentsPage } from "./DocumentsPage";
import "./styles.css";

export const documentsModuleEntry = {
  id: "documents",
  pages: [{ id: "documents", icon: "file", component: DocumentsPage }],
} as const satisfies FrontendModuleEntry;
