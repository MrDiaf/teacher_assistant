import { AiAccountSettings } from "../ai/AiAccountSettings";
import { useRegisteredSettingsPanels } from "./settingsPanelHost";

export function SettingsPage() {
  const panels = useRegisteredSettingsPanels();

  return (
    <main className="settings-page" aria-labelledby="settings-title">
      <header className="module-heading">
        <div>
          <p className="eyebrow">Private configuration</p>
          <h1 id="settings-title">Settings</h1>
          <p>
            Manage private services for this Teacher Assistant installation.
          </p>
        </div>
      </header>

      <AiAccountSettings />

      {panels.map((panel) => {
        const Panel = panel.component;
        return <Panel key={panel.id} />;
      })}
    </main>
  );
}
