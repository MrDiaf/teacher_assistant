import { useState } from "react";

import type { PageId } from "./platform/modules/contract";
import {
  registeredPages,
  registeredSettingsPanels,
} from "./platform/modules/frontendCatalog";
import { getActiveModule, setActiveModule } from "./platform/persistence";
import { RegisteredApplication } from "./platform/shell";

export default function App() {
  const [activeModule, setActiveModuleState] =
    useState<PageId>(getActiveModule);

  function navigate(module: PageId) {
    setActiveModuleState(module);
    setActiveModule(module);
  }

  return (
    <RegisteredApplication
      activePage={activeModule}
      onNavigate={navigate}
      pages={registeredPages}
      settingsPanels={registeredSettingsPanels}
    />
  );
}
