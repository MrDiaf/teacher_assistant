import type { ModuleId } from "../components/AppShell";
import type { CalendarView } from "../features/calendar/types";
import type { CourseTab } from "../features/courses/types";

export const UI_STATE_STORAGE_KEY = "teacher-assistant.ui-state.v1";
export const UI_STATE_VERSION = 1;
export const MAX_ASSISTANT_DRAFT_LENGTH = 4_000;
export const MAX_ASSISTANT_DRAFTS = 20;

const MAX_COURSE_CALENDARS = 50;
const NEW_CONVERSATION_DRAFT_KEY = "new";
const MODULES: readonly ModuleId[] = [
  "dashboard",
  "calendar",
  "courses",
  "inbox",
  "study-plan",
  "assistant",
  "settings",
];
const CALENDAR_VIEWS: readonly CalendarView[] = ["day", "week", "month"];
const COURSE_TABS: readonly CourseTab[] = [
  "overview",
  "notes",
  "materials",
  "calendar",
];
const ASSISTANT_SIDEBAR_MODES = ["conversations", "activity"] as const;

export type AssistantSidebarMode = (typeof ASSISTANT_SIDEBAR_MODES)[number];

export interface CalendarPreference {
  view: CalendarView;
  anchor: string;
}

export interface CourseSelection {
  courseId: string;
  tab: CourseTab;
}

export interface AssistantPreference {
  conversationId?: string | null;
  sidebarMode: AssistantSidebarMode;
}

interface StoredCalendarPreference extends CalendarPreference {
  updatedAt: number;
}

interface StoredDraft {
  text: string;
  updatedAt: number;
}

interface PersistedUiState {
  version: 1;
  activeModule?: ModuleId;
  calendars?: {
    main?: StoredCalendarPreference;
    courses?: Record<string, StoredCalendarPreference>;
  };
  courseSelection?: CourseSelection;
  assistant?: {
    conversationId?: string | null;
    sidebarMode?: AssistantSidebarMode;
    drafts?: Record<string, StoredDraft>;
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isUuid(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      value,
    )
  );
}

export function isLocalDate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const [year, month, day] = value.split("-").map(Number);
  const candidate = new Date(year, month - 1, day);
  return (
    candidate.getFullYear() === year &&
    candidate.getMonth() === month - 1 &&
    candidate.getDate() === day
  );
}

function isTimestamp(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function parseCalendarPreference(
  value: unknown,
): StoredCalendarPreference | undefined {
  if (!isRecord(value)) return undefined;
  if (
    !CALENDAR_VIEWS.includes(value.view as CalendarView) ||
    !isLocalDate(value.anchor) ||
    !isTimestamp(value.updatedAt)
  ) {
    return undefined;
  }
  return {
    view: value.view as CalendarView,
    anchor: value.anchor,
    updatedAt: value.updatedAt,
  };
}

function sanitizeState(value: unknown): PersistedUiState | null {
  if (!isRecord(value) || value.version !== UI_STATE_VERSION) return null;

  const result: PersistedUiState = { version: UI_STATE_VERSION };
  if (MODULES.includes(value.activeModule as ModuleId)) {
    result.activeModule = value.activeModule as ModuleId;
  }

  if (isRecord(value.calendars)) {
    const main = parseCalendarPreference(value.calendars.main);
    const courses: Record<string, StoredCalendarPreference> = {};
    if (isRecord(value.calendars.courses)) {
      Object.entries(value.calendars.courses)
        .filter(([courseId]) => isUuid(courseId))
        .map(
          ([courseId, preference]) =>
            [courseId, parseCalendarPreference(preference)] as const,
        )
        .filter(
          (entry): entry is readonly [string, StoredCalendarPreference] =>
            entry[1] !== undefined,
        )
        .sort((first, second) => second[1].updatedAt - first[1].updatedAt)
        .slice(0, MAX_COURSE_CALENDARS)
        .forEach(([courseId, preference]) => {
          courses[courseId] = preference;
        });
    }
    if (main || Object.keys(courses).length > 0) {
      result.calendars = {
        ...(main ? { main } : {}),
        ...(Object.keys(courses).length > 0 ? { courses } : {}),
      };
    }
  }

  if (
    isRecord(value.courseSelection) &&
    isUuid(value.courseSelection.courseId) &&
    COURSE_TABS.includes(value.courseSelection.tab as CourseTab)
  ) {
    result.courseSelection = {
      courseId: value.courseSelection.courseId,
      tab: value.courseSelection.tab as CourseTab,
    };
  }

  if (isRecord(value.assistant)) {
    const assistant: NonNullable<PersistedUiState["assistant"]> = {};
    if (
      value.assistant.conversationId === null ||
      isUuid(value.assistant.conversationId)
    ) {
      assistant.conversationId = value.assistant.conversationId;
    }
    if (
      ASSISTANT_SIDEBAR_MODES.includes(
        value.assistant.sidebarMode as AssistantSidebarMode,
      )
    ) {
      assistant.sidebarMode = value.assistant
        .sidebarMode as AssistantSidebarMode;
    }
    if (isRecord(value.assistant.drafts)) {
      const drafts: Record<string, StoredDraft> = {};
      const activeDraftKey =
        assistant.conversationId === null
          ? NEW_CONVERSATION_DRAFT_KEY
          : assistant.conversationId;
      Object.entries(value.assistant.drafts)
        .filter(
          ([key, draft]) =>
            (key === NEW_CONVERSATION_DRAFT_KEY || isUuid(key)) &&
            isRecord(draft) &&
            typeof draft.text === "string" &&
            draft.text.length <= MAX_ASSISTANT_DRAFT_LENGTH &&
            isTimestamp(draft.updatedAt),
        )
        .sort((first, second) => {
          if (first[0] === activeDraftKey) return -1;
          if (second[0] === activeDraftKey) return 1;
          return (
            (second[1] as StoredDraft).updatedAt -
            (first[1] as StoredDraft).updatedAt
          );
        })
        .slice(0, MAX_ASSISTANT_DRAFTS)
        .forEach(([key, draft]) => {
          const typedDraft = draft as StoredDraft;
          drafts[key] = {
            text: typedDraft.text,
            updatedAt: typedDraft.updatedAt,
          };
        });
      if (Object.keys(drafts).length > 0) assistant.drafts = drafts;
    }
    if (Object.keys(assistant).length > 0) result.assistant = assistant;
  }

  return result;
}

function removeStoredState(): void {
  try {
    window.localStorage.removeItem(UI_STATE_STORAGE_KEY);
  } catch {
    // Browser storage is optional convenience state.
  }
}

function readState(): PersistedUiState {
  try {
    const raw = window.localStorage.getItem(UI_STATE_STORAGE_KEY);
    if (raw === null) return { version: UI_STATE_VERSION };
    const parsed: unknown = JSON.parse(raw);
    const sanitized = sanitizeState(parsed);
    if (!sanitized) {
      removeStoredState();
      return { version: UI_STATE_VERSION };
    }
    const canonical = JSON.stringify(sanitized);
    if (canonical !== raw)
      window.localStorage.setItem(UI_STATE_STORAGE_KEY, canonical);
    return sanitized;
  } catch {
    removeStoredState();
    return { version: UI_STATE_VERSION };
  }
}

function writeState(state: PersistedUiState): void {
  try {
    window.localStorage.setItem(UI_STATE_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Full, disabled, or unavailable storage must not interrupt the application.
  }
}

function updateState(update: (state: PersistedUiState) => void): void {
  const state = readState();
  update(state);
  writeState(state);
}

function draftKey(conversationId: string | null): string | null {
  if (conversationId === null) return NEW_CONVERSATION_DRAFT_KEY;
  return isUuid(conversationId) ? conversationId : null;
}

export function getActiveModule(): ModuleId {
  return readState().activeModule ?? "calendar";
}

export function setActiveModule(module: ModuleId): void {
  if (!MODULES.includes(module)) return;
  updateState((state) => {
    state.activeModule = module;
  });
}

export function getCalendarPreference(
  courseId?: string,
): CalendarPreference | undefined {
  const state = readState();
  const stored = courseId
    ? isUuid(courseId)
      ? state.calendars?.courses?.[courseId]
      : undefined
    : state.calendars?.main;
  return stored ? { view: stored.view, anchor: stored.anchor } : undefined;
}

export function setCalendarPreference(
  preference: CalendarPreference,
  courseId?: string,
): void {
  if (
    !CALENDAR_VIEWS.includes(preference.view) ||
    !isLocalDate(preference.anchor) ||
    (courseId !== undefined && !isUuid(courseId))
  ) {
    return;
  }
  updateState((state) => {
    const calendars = (state.calendars ??= {});
    const stored = { ...preference, updatedAt: Date.now() };
    if (courseId) {
      const courses = (calendars.courses ??= {});
      courses[courseId] = stored;
      const retained = Object.entries(courses)
        .sort((first, second) => second[1].updatedAt - first[1].updatedAt)
        .slice(0, MAX_COURSE_CALENDARS);
      calendars.courses = Object.fromEntries(retained);
    } else {
      calendars.main = stored;
    }
  });
}

export function removeCourseCalendarPreference(courseId: string): void {
  if (!isUuid(courseId)) return;
  updateState((state) => {
    if (!state.calendars?.courses) return;
    delete state.calendars.courses[courseId];
  });
}

export function pruneCourseCalendars(existingCourseIds: string[]): void {
  const existing = new Set(existingCourseIds.filter(isUuid));
  updateState((state) => {
    const courses = state.calendars?.courses;
    if (!courses) return;
    Object.keys(courses).forEach((courseId) => {
      if (!existing.has(courseId)) delete courses[courseId];
    });
  });
}

export function getCourseSelection(): CourseSelection | null {
  return readState().courseSelection ?? null;
}

export function setCourseSelection(selection: CourseSelection): void {
  if (!isUuid(selection.courseId) || !COURSE_TABS.includes(selection.tab))
    return;
  updateState((state) => {
    state.courseSelection = selection;
  });
}

export function clearCourseSelection(): void {
  updateState((state) => {
    delete state.courseSelection;
  });
}

export function getAssistantPreference(): AssistantPreference {
  const assistant = readState().assistant;
  return {
    ...(assistant && "conversationId" in assistant
      ? { conversationId: assistant.conversationId }
      : {}),
    sidebarMode: assistant?.sidebarMode ?? "conversations",
  };
}

export function setAssistantConversation(conversationId: string | null): void {
  if (conversationId !== null && !isUuid(conversationId)) return;
  updateState((state) => {
    const assistant = (state.assistant ??= {});
    assistant.conversationId = conversationId;
  });
}

export function setAssistantSidebarMode(mode: AssistantSidebarMode): void {
  if (!ASSISTANT_SIDEBAR_MODES.includes(mode)) return;
  updateState((state) => {
    const assistant = (state.assistant ??= {});
    assistant.sidebarMode = mode;
  });
}

export function getAssistantDraft(conversationId: string | null): string {
  const key = draftKey(conversationId);
  return key ? (readState().assistant?.drafts?.[key]?.text ?? "") : "";
}

export function setAssistantDraft(
  conversationId: string | null,
  text: string,
): void {
  const key = draftKey(conversationId);
  if (key === null || text.length > MAX_ASSISTANT_DRAFT_LENGTH) return;
  if (text.length === 0) {
    clearAssistantDraft(conversationId);
    return;
  }
  updateState((state) => {
    const assistant = (state.assistant ??= {});
    const drafts = (assistant.drafts ??= {});
    drafts[key] = { text, updatedAt: Date.now() };
    const activeKey =
      assistant.conversationId === null
        ? NEW_CONVERSATION_DRAFT_KEY
        : assistant.conversationId;
    const retained = Object.entries(drafts)
      .sort(([firstKey, first], [secondKey, second]) => {
        if (firstKey === key) return -1;
        if (secondKey === key) return 1;
        if (firstKey === activeKey) return -1;
        if (secondKey === activeKey) return 1;
        return second.updatedAt - first.updatedAt;
      })
      .slice(0, MAX_ASSISTANT_DRAFTS);
    assistant.drafts = Object.fromEntries(retained);
  });
}

export function clearAssistantDraft(conversationId: string | null): void {
  const key = draftKey(conversationId);
  if (key === null) return;
  updateState((state) => {
    if (!state.assistant?.drafts) return;
    delete state.assistant.drafts[key];
  });
}

export function moveAssistantDraft(
  fromConversationId: string | null,
  toConversationId: string,
): void {
  const fromKey = draftKey(fromConversationId);
  const toKey = draftKey(toConversationId);
  if (!fromKey || !toKey) return;
  updateState((state) => {
    const drafts = state.assistant?.drafts;
    if (!drafts?.[fromKey]) return;
    drafts[toKey] = drafts[fromKey];
    delete drafts[fromKey];
  });
}

export function removeAssistantConversation(conversationId: string): void {
  if (!isUuid(conversationId)) return;
  updateState((state) => {
    const assistant = state.assistant;
    if (!assistant) return;
    if (assistant.conversationId === conversationId) {
      delete assistant.conversationId;
    }
    if (assistant.drafts) delete assistant.drafts[conversationId];
  });
}

export function pruneAssistantConversations(existingIds: string[]): void {
  const validIds = new Set(existingIds.filter(isUuid));
  updateState((state) => {
    const assistant = state.assistant;
    if (!assistant) return;
    if (
      typeof assistant.conversationId === "string" &&
      !validIds.has(assistant.conversationId)
    ) {
      delete assistant.conversationId;
    }
    if (!assistant.drafts) return;
    Object.keys(assistant.drafts).forEach((key) => {
      if (key !== NEW_CONVERSATION_DRAFT_KEY && !validIds.has(key)) {
        delete assistant.drafts![key];
      }
    });
  });
}
