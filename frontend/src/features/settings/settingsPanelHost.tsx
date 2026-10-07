import { createContext, useContext, type ReactNode } from "react";

import type { RegisteredSettingsPanel } from "../../platform/modules/frontendContract";

const SettingsPanelsContext = createContext<
  readonly RegisteredSettingsPanel[] | null
>(null);

export function RegisteredSettingsPanelsProvider({
  children,
  panels,
}: {
  children: ReactNode;
  panels: readonly RegisteredSettingsPanel[];
}) {
  return (
    <SettingsPanelsContext.Provider value={panels}>
      {children}
    </SettingsPanelsContext.Provider>
  );
}

export function useRegisteredSettingsPanels(): readonly RegisteredSettingsPanel[] {
  const panels = useContext(SettingsPanelsContext);
  if (panels === null) {
    throw new Error(
      "Settings must render inside the registered Settings host.",
    );
  }
  return panels;
}
