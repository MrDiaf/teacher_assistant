import type { ComponentType } from "react";

import type { IconName } from "../ui";
import type { ModuleCatalog, ModuleId, PageId } from "./contract";

export interface PageCodeContribution<TPageId extends string = PageId> {
  readonly id: TPageId;
  readonly icon: IconName;
  readonly component: ComponentType;
}

export interface SettingsPanelCodeContribution<
  TSettingsPanelId extends string = string,
> {
  readonly id: TSettingsPanelId;
  readonly component: ComponentType;
}

export interface FrontendModuleEntry<
  TModuleId extends string = ModuleId,
  TPageId extends string = PageId,
  TSettingsPanelId extends string = string,
> {
  readonly id: TModuleId;
  readonly pages: readonly PageCodeContribution<TPageId>[];
  readonly settingsPanels: readonly SettingsPanelCodeContribution<TSettingsPanelId>[];
}

export interface RegisteredPage<TPageId extends string = PageId>
  extends PageCodeContribution<TPageId> {
  readonly moduleId: string;
  readonly label: string;
  readonly order: number;
}

export interface RegisteredSettingsPanel<
  TSettingsPanelId extends string = string,
> extends SettingsPanelCodeContribution<TSettingsPanelId> {
  readonly moduleId: string;
  readonly label: string;
  readonly order: number;
}

export function assembleFrontendPages<
  TModuleId extends string,
  TPageId extends string,
>(
  catalog: ModuleCatalog,
  entries: readonly FrontendModuleEntry<TModuleId, TPageId>[],
): readonly RegisteredPage<TPageId>[] {
  const entriesById = new Map<
    string,
    FrontendModuleEntry<TModuleId, TPageId>
  >();
  for (const entry of entries) {
    if (entriesById.has(entry.id)) {
      throw new Error(
        `Duplicate frontend module entry: ${JSON.stringify(entry.id)}`,
      );
    }
    entriesById.set(entry.id, entry);
  }

  const knownModuleIds = new Set(
    catalog.registrations.map((registration) => registration.id),
  );
  for (const entry of entries) {
    if (!knownModuleIds.has(entry.id)) {
      throw new Error(
        `Unknown frontend module entry: ${JSON.stringify(entry.id)}`,
      );
    }
  }

  const pages: RegisteredPage<TPageId>[] = [];
  for (const registration of catalog.registrations) {
    const entry = entriesById.get(registration.id);
    if (entry === undefined) {
      throw new Error(
        `Missing frontend module entry: ${JSON.stringify(registration.id)}`,
      );
    }
    const pagesById = new Map<string, PageCodeContribution<TPageId>>();
    for (const page of entry.pages) {
      if (pagesById.has(page.id)) {
        throw new Error(
          `Duplicate frontend page code contribution: ${JSON.stringify(page.id)}`,
        );
      }
      pagesById.set(page.id, page);
    }

    const expectedPageIds = new Set(
      registration.contributions.pages.map((page) => page.id),
    );
    for (const page of entry.pages) {
      if (!expectedPageIds.has(page.id)) {
        throw new Error(
          `Unknown frontend page code contribution ${JSON.stringify(page.id)} for module ${JSON.stringify(entry.id)}`,
        );
      }
    }
    for (const metadata of registration.contributions.pages) {
      const page = pagesById.get(metadata.id);
      if (page === undefined) {
        throw new Error(
          `Missing frontend page code contribution ${JSON.stringify(metadata.id)} for module ${JSON.stringify(entry.id)}`,
        );
      }
      if (registration.enabled_by_default) {
        pages.push(
          Object.freeze({
            ...page,
            moduleId: registration.id,
            label: metadata.label,
            order: metadata.order,
          }),
        );
      }
    }
  }

  return Object.freeze(pages.sort((left, right) => left.order - right.order));
}

export function assembleFrontendSettingsPanels<
  TModuleId extends string,
  TPageId extends string,
  TSettingsPanelId extends string,
>(
  catalog: ModuleCatalog,
  entries: readonly FrontendModuleEntry<TModuleId, TPageId, TSettingsPanelId>[],
): readonly RegisteredSettingsPanel<TSettingsPanelId>[] {
  const entriesById = new Map<
    string,
    FrontendModuleEntry<TModuleId, TPageId, TSettingsPanelId>
  >();
  for (const entry of entries) {
    if (entriesById.has(entry.id)) {
      throw new Error(
        `Duplicate frontend module entry: ${JSON.stringify(entry.id)}`,
      );
    }
    entriesById.set(entry.id, entry);
  }

  const knownModuleIds = new Set(
    catalog.registrations.map((registration) => registration.id),
  );
  for (const entry of entries) {
    if (!knownModuleIds.has(entry.id)) {
      throw new Error(
        `Unknown frontend module entry: ${JSON.stringify(entry.id)}`,
      );
    }
  }

  const panels: RegisteredSettingsPanel<TSettingsPanelId>[] = [];
  for (const registration of catalog.registrations) {
    const entry = entriesById.get(registration.id);
    if (entry === undefined) {
      throw new Error(
        `Missing frontend module entry: ${JSON.stringify(registration.id)}`,
      );
    }
    const panelsById = new Map<
      string,
      SettingsPanelCodeContribution<TSettingsPanelId>
    >();
    for (const panel of entry.settingsPanels) {
      if (panelsById.has(panel.id)) {
        throw new Error(
          `Duplicate frontend Settings panel code contribution: ${JSON.stringify(panel.id)}`,
        );
      }
      panelsById.set(panel.id, panel);
    }

    const expectedPanelIds = new Set(
      registration.contributions.settings_panels.map((panel) => panel.id),
    );
    for (const panel of entry.settingsPanels) {
      if (!expectedPanelIds.has(panel.id)) {
        throw new Error(
          `Unknown frontend Settings panel code contribution ${JSON.stringify(panel.id)} for module ${JSON.stringify(entry.id)}`,
        );
      }
    }
    for (const metadata of registration.contributions.settings_panels) {
      const panel = panelsById.get(metadata.id);
      if (panel === undefined) {
        throw new Error(
          `Missing frontend Settings panel code contribution ${JSON.stringify(metadata.id)} for module ${JSON.stringify(entry.id)}`,
        );
      }
      if (registration.enabled_by_default) {
        panels.push(
          Object.freeze({
            ...panel,
            moduleId: registration.id,
            label: metadata.label,
            order: metadata.order,
          }),
        );
      }
    }
  }

  return Object.freeze(panels.sort((left, right) => left.order - right.order));
}
