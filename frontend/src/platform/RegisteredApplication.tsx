import { AppShell } from "../components/AppShell";
import { RegisteredSettingsPanelsProvider } from "../features/settings/settingsPanelHost";
import type {
  RegisteredPage,
  RegisteredSettingsPanel,
} from "./modules/frontendContract";

export function RegisteredApplication<TPageId extends string>({
  activePage,
  onNavigate,
  pages,
  settingsPanels,
}: {
  activePage: TPageId;
  onNavigate: (page: TPageId) => void;
  pages: readonly RegisteredPage<TPageId>[];
  settingsPanels: readonly RegisteredSettingsPanel[];
}) {
  const page = pages.find((candidate) => candidate.id === activePage);
  if (page === undefined) {
    throw new Error(`No registered page for ${JSON.stringify(activePage)}`);
  }
  const Page = page.component;
  return (
    <RegisteredSettingsPanelsProvider panels={settingsPanels}>
      <AppShell
        activeModule={activePage}
        navigation={pages}
        onNavigate={onNavigate}
      >
        <Page />
      </AppShell>
    </RegisteredSettingsPanelsProvider>
  );
}
