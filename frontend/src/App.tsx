import { useState } from "react";

import { AppShell, type ModuleId } from "./components/AppShell";
import { Icon } from "./components/Icon";
import { AssistantPage } from "./features/assistant/AssistantPage";
import { CalendarPage } from "./features/calendar/CalendarPage";
import { CoursesPage } from "./features/courses/CoursesPage";
import { InboxPage } from "./features/inbox/InboxPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { getActiveModule, setActiveModule } from "./persistence/uiState";

const PLACEHOLDER_COPY: Record<
  Exclude<
    ModuleId,
    "calendar" | "assistant" | "courses" | "inbox" | "settings"
  >,
  [string, string]
> = {
  dashboard: [
    "Dashboard",
    "Your teaching overview will come together here in a later phase.",
  ],
  "study-plan": [
    "Study Plan",
    "Study planning tools are coming in a later phase.",
  ],
};

function PlaceholderPage({
  module,
}: {
  module: Exclude<
    ModuleId,
    "calendar" | "assistant" | "courses" | "inbox" | "settings"
  >;
}) {
  const [title, copy] = PLACEHOLDER_COPY[module];
  return (
    <main className="placeholder-page" aria-labelledby="placeholder-title">
      <div className="placeholder-mark" aria-hidden="true">
        <Icon name="leaf" size={28} />
      </div>
      <p className="eyebrow">Teacher Assistant</p>
      <h1 id="placeholder-title">{title}</h1>
      <p>{copy}</p>
      <span>Coming in a later phase</span>
    </main>
  );
}

export default function App() {
  const [activeModule, setActiveModuleState] =
    useState<ModuleId>(getActiveModule);

  function navigate(module: ModuleId) {
    setActiveModuleState(module);
    setActiveModule(module);
  }

  return (
    <AppShell activeModule={activeModule} onNavigate={navigate}>
      {activeModule === "calendar" && <CalendarPage />}
      {activeModule === "courses" && <CoursesPage />}
      {activeModule === "inbox" && <InboxPage />}
      {activeModule === "assistant" && <AssistantPage />}
      {activeModule === "settings" && <SettingsPage />}
      {activeModule !== "calendar" &&
        activeModule !== "courses" &&
        activeModule !== "assistant" &&
        activeModule !== "inbox" &&
        activeModule !== "settings" && (
          <PlaceholderPage module={activeModule} />
        )}
    </AppShell>
  );
}
