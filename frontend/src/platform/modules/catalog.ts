import catalogJson from "./catalog.json";
import { parseModuleCatalog } from "./contract";

export const moduleCatalog = parseModuleCatalog(catalogJson);
