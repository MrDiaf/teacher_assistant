import { useState } from "react";

import type { PageId } from "./platform/modules/contract";
import { assembleModuleHostPages } from "./platform/modules/moduleHost";
import { RegisteredApplication } from "./platform/shell";

export default function ModuleHost({ moduleId }: { moduleId: string }) {
  const pages = assembleModuleHostPages(moduleId);
  const [activePage, setActivePage] = useState<PageId>(pages[0].id);

  return (
    <RegisteredApplication
      activePage={activePage}
      onNavigate={setActivePage}
      pages={pages}
    />
  );
}
