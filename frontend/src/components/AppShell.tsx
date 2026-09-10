import type { ReactNode } from "react";

import { Icon, type IconName } from "./Icon";
import type { PageId } from "../platform/modules/contract";

export type ModuleId = PageId;

export interface NavigationItem<TPageId extends string = PageId> {
  id: TPageId;
  label: string;
  icon: IconName;
}

interface AppShellProps<TPageId extends string> {
  activeModule: TPageId;
  children: ReactNode;
  navigation: readonly NavigationItem<TPageId>[];
  onNavigate: (module: TPageId) => void;
}

export function AppShell<TPageId extends string>({
  activeModule,
  children,
  navigation,
  onNavigate,
}: AppShellProps<TPageId>) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
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
          {navigation.map((item) => (
            <button
              className={
                item.id === activeModule ? "nav-item active" : "nav-item"
              }
              aria-current={item.id === activeModule ? "page" : undefined}
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
          <span className="privacy-dot" aria-hidden="true" />
          <span>
            <strong>Private workspace</strong>
            <small>Stored on this installation</small>
          </span>
        </div>
      </aside>
      <div className="app-content" id="main-content" tabIndex={-1}>
        {children}
      </div>
    </div>
  );
}
