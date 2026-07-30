import type { CourseModel, CourseMutation } from "./types";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    const validationMessage = Array.isArray(payload?.detail)
      ? payload.detail[0]?.msg
      : payload?.detail;
    throw new CourseApiError(
      payload?.message ??
        validationMessage ??
        "The course request could not be completed.",
    );
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
};
