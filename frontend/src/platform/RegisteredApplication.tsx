import { AppShell } from "../components/AppShell";
import type { RegisteredPage } from "./modules/frontendContract";

export function RegisteredApplication<TPageId extends string>({
  activePage,
  onNavigate,
  pages,
}: {
  activePage: TPageId;
  onNavigate: (page: TPageId) => void;
  pages: readonly RegisteredPage<TPageId>[];
}) {
  const page = pages.find((candidate) => candidate.id === activePage);
  if (page === undefined) {
    throw new Error(`No registered page for ${JSON.stringify(activePage)}`);
  }
  const Page = page.component;
  return (
    <AppShell
      activeModule={activePage}
      navigation={pages}
      onNavigate={onNavigate}
    >
      <Page />
    </AppShell>
  );
}
