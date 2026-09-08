import type { DocumentProject, DocumentTag } from "./types";

interface ErrorPayload {
  message?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let payload: ErrorPayload = {};
    try {
      payload = (await response.json()) as ErrorPayload;
    } catch {
      // The API's safe fallback message is used below.
    }
    throw new Error(
      payload.message ?? "The document request could not be completed.",
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const documentsApi = {
  list(search: string, tagId: string | null, signal?: AbortSignal) {
    const query = new URLSearchParams();
    if (search.trim()) query.set("search", search.trim());
    if (tagId) query.set("tag_id", tagId);
    return request<DocumentProject[]>(`/document-projects?${query}`, {
      signal,
    });
  },
  get(projectId: string) {
    return request<DocumentProject>(
      `/document-projects/${encodeURIComponent(projectId)}`,
    );
  },
  create(title: string) {
    return request<DocumentProject>("/document-projects", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  },
  rename(projectId: string, title: string) {
    return request<DocumentProject>(
      `/document-projects/${encodeURIComponent(projectId)}`,
      { method: "PATCH", body: JSON.stringify({ title }) },
    );
  },
  delete(projectId: string) {
    return request<void>(
      `/document-projects/${encodeURIComponent(projectId)}`,
      { method: "DELETE" },
    );
  },
  listTags(signal?: AbortSignal) {
    return request<DocumentTag[]>("/document-tags", { signal });
  },
  createTag(name: string, color: string) {
    return request<DocumentTag>("/document-tags", {
      method: "POST",
      body: JSON.stringify({ name, color }),
    });
  },
  updateTag(tagId: string, values: { name?: string; color?: string }) {
    return request<DocumentTag>(`/document-tags/${encodeURIComponent(tagId)}`, {
      method: "PATCH",
      body: JSON.stringify(values),
    });
  },
  deleteTag(tagId: string) {
    return request<void>(`/document-tags/${encodeURIComponent(tagId)}`, {
      method: "DELETE",
    });
  },
  assignTag(projectId: string, tagId: string) {
    return request<DocumentProject>(
      `/document-projects/${encodeURIComponent(projectId)}/tags/${encodeURIComponent(tagId)}`,
      { method: "PUT" },
    );
  },
  unassignTag(projectId: string, tagId: string) {
    return request<DocumentProject>(
      `/document-projects/${encodeURIComponent(projectId)}/tags/${encodeURIComponent(tagId)}`,
      { method: "DELETE" },
    );
  },
  mainTexUrl(projectId: string) {
    return `/api/v1/document-projects/${encodeURIComponent(projectId)}/main.tex`;
  },
  sourceZipUrl(projectId: string) {
    return `/api/v1/document-projects/${encodeURIComponent(projectId)}/source.zip`;
  },
};
