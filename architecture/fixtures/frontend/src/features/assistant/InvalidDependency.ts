import type { DocumentProject } from "../documents/types";

export const invalidDependency = (project: DocumentProject): string => project.id;
