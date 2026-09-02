import type {
  CourseMaterialType,
  CourseModel,
  CourseMutation,
  CourseNote,
  CourseSource,
  NoteMutation,
  NotePrettifySuggestion,
  NoteSummary,
} from "./types";
import type { CalendarEvent, CalendarModel } from "../calendar/types";

interface ApiErrorPayload {
  error_id?: string;
  code?: string;
  message?: string;
  details?: Record<string, unknown>;
  request_id?: string;
  detail?: string | { msg?: string }[];
}

export class CourseApiError extends Error {
  readonly status: number;
  readonly errorId: string | null;
  readonly code: string | null;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;

  constructor(message: string, response: Response, payload?: ApiErrorPayload) {
    super(message);
    this.name = "CourseApiError";
    this.status = response.status;
    this.errorId = payload?.error_id ?? null;
    this.code = payload?.code ?? null;
    this.details = payload?.details ?? {};
    this.requestId = payload?.request_id ?? null;
  }
}

async function readApiError(response: Response): Promise<CourseApiError> {
  let payload: ApiErrorPayload | undefined;
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = undefined;
  }
  const validationMessage = Array.isArray(payload?.detail)
    ? payload.detail[0]?.msg
    : payload?.detail;
  return new CourseApiError(
    payload?.message ??
      validationMessage ??
      "The course request could not be completed.",
    response,
    payload,
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw await readApiError(response);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function sourceContentUrl(sourceId: string) {
  return `/api/v1/course-sources/${encodeURIComponent(sourceId)}/content`;
}

export const courseApi = {
  list(signal?: AbortSignal) {
    return request<CourseModel[]>("/courses", { signal });
  },

  create(payload: CourseMutation) {
    return request<CourseModel>("/courses", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  update(courseId: string, payload: CourseMutation) {
    return request<CourseModel>(`/courses/${courseId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  archive(courseId: string) {
    return request<CourseModel>(`/courses/${courseId}/archive`, {
      method: "POST",
    });
  },

  restore(courseId: string) {
    return request<CourseModel>(`/courses/${courseId}/restore`, {
      method: "POST",
    });
  },

  delete(courseId: string) {
    return request<void>(`/courses/${courseId}`, { method: "DELETE" });
  },

  listCalendars(courseId: string, signal?: AbortSignal) {
    return request<CalendarModel[]>(`/courses/${courseId}/calendars`, {
      signal,
    });
  },

  linkCalendar(courseId: string, calendarId: string) {
    return request<CalendarModel>(`/courses/${courseId}/calendars`, {
      method: "POST",
      body: JSON.stringify({ calendar_id: calendarId }),
    });
  },

  unlinkCalendar(courseId: string, calendarId: string) {
    return request<void>(`/courses/${courseId}/calendars/${calendarId}`, {
      method: "DELETE",
    });
  },

  listEvents(
    courseId: string,
    startsBefore: Date,
    endsAfter: Date,
    options?: {
      calendarId?: string;
      search?: string;
      signal?: AbortSignal;
    },
  ) {
    const query = new URLSearchParams({
      starts_before: startsBefore.toISOString(),
      ends_after: endsAfter.toISOString(),
    });
    if (options?.calendarId) {
      query.set("calendar_id", options.calendarId);
    }
    if (options?.search) {
      query.set("search", options.search);
    }
    return request<CalendarEvent[]>(
      `/courses/${courseId}/events?${query.toString()}`,
      { signal: options?.signal },
    );
  },

  listSources(
    courseId: string,
    signal?: AbortSignal,
    sourceType?: CourseMaterialType,
  ) {
    const query = sourceType
      ? `?${new URLSearchParams({ source_type: sourceType }).toString()}`
      : "";
    return request<CourseSource[]>(`/courses/${courseId}/sources${query}`, {
      signal,
    });
  },

  async uploadSource(
    courseId: string,
    sourceType: CourseMaterialType,
    file: File,
  ) {
    const query = new URLSearchParams({
      source_type: sourceType,
      file_name: file.name,
    });
    const response = await fetch(
      `/api/v1/courses/${courseId}/sources?${query.toString()}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: file,
      },
    );
    if (!response.ok) throw await readApiError(response);
    return (await response.json()) as CourseSource;
  },

  deleteSource(sourceId: string) {
    return request<void>(`/course-sources/${sourceId}`, { method: "DELETE" });
  },

  retrySourceExtraction(sourceId: string) {
    return request<CourseSource>(
      `/course-sources/${sourceId}/retry-extraction`,
      { method: "POST" },
    );
  },

  sourceContentUrl,

  async probeSourceContent(sourceId: string, signal?: AbortSignal) {
    const response = await fetch(sourceContentUrl(sourceId), {
      headers: {
        Accept: "application/pdf",
        Range: "bytes=0-0",
      },
      signal,
    });
    if (!response.ok) throw await readApiError(response);
    if (!response.headers.get("Content-Type")?.startsWith("application/pdf")) {
      throw new CourseApiError(
        "The course material did not return a supported PDF.",
        response,
      );
    }
  },

  listNotes(courseId: string, signal?: AbortSignal) {
    return request<CourseNote[]>(`/courses/${courseId}/notes`, { signal });
  },

  createNote(courseId: string, payload: NoteMutation) {
    return request<CourseNote>(`/courses/${courseId}/notes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updateNote(noteId: string, payload: NoteMutation) {
    return request<CourseNote>(`/notes/${noteId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  deleteNote(noteId: string) {
    return request<void>(`/notes/${noteId}`, { method: "DELETE" });
  },

  prettifyNote(body: string, model: string, signal?: AbortSignal) {
    return request<NotePrettifySuggestion>("/notes/prettify", {
      method: "POST",
      body: JSON.stringify({ body, model }),
      signal,
    });
  },

  getNoteSummary(noteId: string, signal?: AbortSignal) {
    return request<NoteSummary | null>(`/notes/${noteId}/summary`, { signal });
  },

  generateNoteSummary(noteId: string, model: string) {
    return request<NoteSummary>(`/notes/${noteId}/summaries`, {
      method: "POST",
      body: JSON.stringify({ model }),
    });
  },

  retryNoteSummary(summaryId: string) {
    return request<NoteSummary>(`/note-summaries/${summaryId}/retry`, {
      method: "POST",
    });
  },

  removeNoteSummaryBullet(summaryId: string, bulletId: string) {
    return request<NoteSummary>(
      `/note-summaries/${summaryId}/bullets/${bulletId}`,
      { method: "DELETE" },
    );
  },
};
