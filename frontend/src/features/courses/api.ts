import type {
  CourseMaterialType,
  CourseModel,
  CourseMutation,
  CourseNote,
  CourseSource,
  NoteMutation,
  NoteSummary,
} from "./types";

interface ApiErrorPayload {
  message?: string;
  detail?: string | { msg?: string }[];
}

class CourseApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CourseApiError";
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
};
