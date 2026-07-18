import { useState } from "react";

import { AppShell, type ModuleId } from "./components/AppShell";
import { Icon } from "./components/Icon";
import { CalendarPage } from "./features/calendar/CalendarPage";

const PLACEHOLDER_COPY: Record<
  Exclude<ModuleId, "calendar">,
  [string, string]
> = {
  dashboard: [
    "Dashboard",
    "Your teaching overview will come together here in a later phase.",
  ],
  courses: ["Courses", "Course organization is planned for a later phase."],
  "study-plan": [
    "Study Plan",
    "Study planning tools are coming in a later phase.",
  ],
  assistant: [
    "Assistant",
    "The calendar assistant will be introduced after the calendar is complete.",
  ],
  settings: [
    "Settings",
    "Application preferences are coming in a later phase.",
  ],
};

function PlaceholderPage({
  module,
}: {
  module: Exclude<ModuleId, "calendar">;
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
  const [activeModule, setActiveModule] = useState<ModuleId>("calendar");

  return (
    <AppShell activeModule={activeModule} onNavigate={setActiveModule}>
      {activeModule === "calendar" ? (
        <CalendarPage />
      ) : (
        <PlaceholderPage module={activeModule} />
      )}
    </AppShell>
  );
}
