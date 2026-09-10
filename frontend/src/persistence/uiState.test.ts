import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  MAX_ASSISTANT_DRAFT_LENGTH,
  MAX_ASSISTANT_DRAFTS,
  UI_STATE_STORAGE_KEY,
  clearAssistantDraft,
  getActiveModule,
  getAssistantDraft,
  getAssistantPreference,
  getCalendarPreference,
  getCourseSelection,
  isLocalDate,
  isUuid,
  pruneAssistantConversations,
  setActiveModule,
  setAssistantConversation,
  setAssistantDraft,
  setAssistantSidebarMode,
  setCalendarPreference,
  setCourseSelection,
} from "../platform/persistence";

const COURSE_ID = "11111111-1111-4111-8111-111111111111";
const CONVERSATION_ID = "22222222-2222-4222-8222-222222222222";

function draftId(index: number): string {
  return `33333333-3333-4333-8333-${String(index).padStart(12, "0")}`;
}

describe("uiState persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("round-trips only supported, versioned UI preferences", () => {
    setActiveModule("courses");
    setCalendarPreference({ view: "day", anchor: "2026-09-02" });
    setCalendarPreference({ view: "week", anchor: "2026-09-07" }, COURSE_ID);
    setCourseSelection({ courseId: COURSE_ID, tab: "notes" });
    setAssistantConversation(CONVERSATION_ID);
    setAssistantSidebarMode("activity");
    setAssistantDraft(CONVERSATION_ID, "Review the schedule");
    setAssistantDraft(null, "A separate new conversation");

    expect(getActiveModule()).toBe("courses");
    expect(getCalendarPreference()).toEqual({
      view: "day",
      anchor: "2026-09-02",
    });
    expect(getCalendarPreference(COURSE_ID)).toEqual({
      view: "week",
      anchor: "2026-09-07",
    });
    expect(getCourseSelection()).toEqual({
      courseId: COURSE_ID,
      tab: "notes",
    });
    expect(getAssistantPreference()).toEqual({
      conversationId: CONVERSATION_ID,
      sidebarMode: "activity",
    });
    expect(getAssistantDraft(CONVERSATION_ID)).toBe("Review the schedule");
    expect(getAssistantDraft(null)).toBe("A separate new conversation");

    const stored = JSON.parse(
      window.localStorage.getItem(UI_STATE_STORAGE_KEY) ?? "null",
    ) as Record<string, unknown>;
    expect(stored.version).toBe(1);
  });

  it("restores the existing storage envelope through the Platform entry point", () => {
    window.localStorage.setItem(
      "teacher-assistant.ui-state.v1",
      JSON.stringify({
        version: 1,
        activeModule: "courses",
        calendars: {
          main: { view: "week", anchor: "2026-09-07", updatedAt: 1 },
          courses: {
            [COURSE_ID]: {
              view: "day",
              anchor: "2026-09-09",
              updatedAt: 2,
            },
          },
        },
        courseSelection: { courseId: COURSE_ID, tab: "materials" },
      }),
    );

    expect(UI_STATE_STORAGE_KEY).toBe("teacher-assistant.ui-state.v1");
    expect(getActiveModule()).toBe("courses");
    expect(getCalendarPreference()).toEqual({
      view: "week",
      anchor: "2026-09-07",
    });
    expect(getCalendarPreference(COURSE_ID)).toEqual({
      view: "day",
      anchor: "2026-09-09",
    });
    expect(getCourseSelection()).toEqual({
      courseId: COURSE_ID,
      tab: "materials",
    });
  });

  it("accepts Documents as a supported module preference", () => {
    setActiveModule("documents");

    expect(getActiveModule()).toBe("documents");
    expect(window.localStorage.getItem(UI_STATE_STORAGE_KEY)).toContain(
      '"activeModule":"documents"',
    );
  });

  it("rejects corrupt, incompatible, and manually injected private data", () => {
    window.localStorage.setItem(UI_STATE_STORAGE_KEY, "not-json");
    expect(getActiveModule()).toBe("calendar");
    expect(window.localStorage.getItem(UI_STATE_STORAGE_KEY)).toBeNull();

    window.localStorage.setItem(
      UI_STATE_STORAGE_KEY,
      JSON.stringify({ version: 2, activeModule: "assistant" }),
    );
    expect(getActiveModule()).toBe("calendar");
    expect(window.localStorage.getItem(UI_STATE_STORAGE_KEY)).toBeNull();

    window.localStorage.setItem(
      UI_STATE_STORAGE_KEY,
      JSON.stringify({
        version: 1,
        activeModule: "secrets",
        credentials: { accessToken: "do-not-retain" },
        events: [{ title: "private event" }],
        proposals: [{ action: "delete_event" }],
        assistant: {
          conversationId: "not-a-uuid",
          sidebarMode: "unknown",
          busy: true,
          drafts: {
            "not-a-uuid": { text: "discard", updatedAt: 1 },
          },
        },
      }),
    );

    expect(getAssistantPreference()).toEqual({ sidebarMode: "conversations" });
    const sanitized = window.localStorage.getItem(UI_STATE_STORAGE_KEY) ?? "";
    expect(sanitized).not.toContain("do-not-retain");
    expect(sanitized).not.toContain("private event");
    expect(sanitized).not.toContain("delete_event");
    expect(sanitized).not.toContain("discard");
  });

  it("validates UUIDs, real calendar dates, views, tabs, and draft size", () => {
    expect(isUuid(COURSE_ID)).toBe(true);
    expect(isUuid("11111111-1111-1111-1111-111111111111")).toBe(false);
    expect(isLocalDate("2024-02-29")).toBe(true);
    expect(isLocalDate("2025-02-29")).toBe(false);

    setCalendarPreference({ view: "day", anchor: "2025-02-29" });
    setCourseSelection({ courseId: "bad-id", tab: "notes" });
    setAssistantDraft(
      CONVERSATION_ID,
      "x".repeat(MAX_ASSISTANT_DRAFT_LENGTH + 1),
    );

    expect(getCalendarPreference()).toBeUndefined();
    expect(getCourseSelection()).toBeNull();
    expect(getAssistantDraft(CONVERSATION_ID)).toBe("");
  });

  it("caps draft count while retaining the draft currently being updated", () => {
    for (let index = 0; index < MAX_ASSISTANT_DRAFTS + 1; index += 1) {
      setAssistantDraft(draftId(index), `draft ${index}`);
    }

    expect(getAssistantDraft(draftId(MAX_ASSISTANT_DRAFTS))).toBe(
      `draft ${MAX_ASSISTANT_DRAFTS}`,
    );
    expect(getAssistantDraft(draftId(0))).toBe("");
    const raw = JSON.parse(
      window.localStorage.getItem(UI_STATE_STORAGE_KEY) ?? "{}",
    ) as { assistant?: { drafts?: Record<string, unknown> } };
    expect(Object.keys(raw.assistant?.drafts ?? {})).toHaveLength(
      MAX_ASSISTANT_DRAFTS,
    );
  });

  it("clears only the requested draft and prunes stale conversation IDs", () => {
    setAssistantConversation(CONVERSATION_ID);
    setAssistantDraft(CONVERSATION_ID, "first");
    setAssistantDraft(draftId(1), "second");
    clearAssistantDraft(CONVERSATION_ID);

    expect(getAssistantDraft(CONVERSATION_ID)).toBe("");
    expect(getAssistantDraft(draftId(1))).toBe("second");

    setAssistantDraft(CONVERSATION_ID, "stale");
    pruneAssistantConversations([draftId(1)]);
    expect(getAssistantDraft(CONVERSATION_ID)).toBe("");
    expect(getAssistantPreference()).toEqual({ sidebarMode: "conversations" });
  });

  it("falls back normally when browser storage reads or writes fail", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("disabled", "SecurityError");
    });
    expect(getActiveModule()).toBe("calendar");
    expect(() => setAssistantDraft(null, "private draft")).not.toThrow();

    vi.restoreAllMocks();
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    expect(() => setActiveModule("assistant")).not.toThrow();
  });
});
