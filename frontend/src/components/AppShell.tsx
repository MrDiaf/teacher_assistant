import type { ReactNode } from "react";

import { Icon, type IconName } from "./Icon";

export type ModuleId =
  | "dashboard"
  | "calendar"
  | "courses"
  | "study-plan"
  | "assistant"
  | "settings";

interface NavigationItem {
  id: ModuleId;
  label: string;
  icon: IconName;
}

const NAVIGATION: NavigationItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "calendar", label: "Calendar", icon: "calendar" },
  { id: "courses", label: "Courses", icon: "courses" },
  { id: "study-plan", label: "Study Plan", icon: "checklist" },
  { id: "assistant", label: "Assistant", icon: "assistant" },
  { id: "settings", label: "Settings", icon: "settings" },
];

interface AppShellProps {
  activeModule: ModuleId;
  children: ReactNode;
  onNavigate: (module: ModuleId) => void;
}

export function AppShell({
  activeModule,
  children,
  onNavigate,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand">
          <span className="brand-symbol">
            <Icon name="leaf" size={25} />
          </span>
          <span>
            <strong>Teacher</strong>
            <small>Assistant</small>
          </span>
        </div>

        <nav className="primary-nav" aria-label="Main navigation">
          {NAVIGATION.map((item) => (
            <button
              className={
                item.id === activeModule ? "nav-item active" : "nav-item"
              }
              key={item.id}
              onClick={() => onNavigate(item.id)}
              type="button"
            >
              <Icon name={item.icon} size={20} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="privacy-dot" />
          <span>
            <strong>Private workspace</strong>
            <small>Stored on this installation</small>
          </span>
        </div>
      </aside>
      <div className="app-content">{children}</div>
    </div>
  );
}
