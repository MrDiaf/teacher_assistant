import type {
  MailCheckResult,
  MailConnectionInput,
  MailConnectionStatus,
  MailListItem,
  MailMessage,
} from "./types";

interface ApiErrorPayload {
  message?: string;
  code?: string;
}

export class MailApiError extends Error {
  readonly code: string | null;
  readonly status: number;

  constructor(message: string, response: Response, payload?: ApiErrorPayload) {
    super(message);
    this.name = "MailApiError";
    this.code = payload?.code ?? null;
    this.status = response.status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    throw new MailApiError(
      payload?.message ?? "The mail request could not be completed.",
      response,
      payload,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const mailApi = {
  status(signal?: AbortSignal) {
    return request<MailConnectionStatus>("/integrations/mail", { signal });
  },
  connect(payload: MailConnectionInput) {
    return request<MailConnectionStatus>("/integrations/mail", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  test() {
    return request<MailConnectionStatus>("/integrations/mail/test", {
      method: "POST",
    });
  },
  check() {
    return request<MailCheckResult>("/integrations/mail/check", {
      method: "POST",
    });
  },
  disconnect() {
    return request<void>("/integrations/mail", { method: "DELETE" });
  },
  list(
    options: { search?: string; archived?: boolean; unreadOnly?: boolean },
    signal?: AbortSignal,
  ) {
    const query = new URLSearchParams();
    if (options.search) query.set("search", options.search);
    if (options.archived) query.set("archived", "true");
    if (options.unreadOnly) query.set("unread_only", "true");
    return request<MailListItem[]>(`/inbox?${query.toString()}`, { signal });
  },
  get(messageId: string, signal?: AbortSignal) {
    return request<MailMessage>(`/inbox/${encodeURIComponent(messageId)}`, {
      signal,
    });
  },
  update(
    messageId: string,
    changes: { is_read?: boolean; is_archived?: boolean },
  ) {
    return request<MailMessage>(`/inbox/${encodeURIComponent(messageId)}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    });
  },
  delete(messageId: string) {
    return request<void>(`/inbox/${encodeURIComponent(messageId)}`, {
      method: "DELETE",
    });
  },
  attachmentUrl(attachmentId: string) {
    return `/api/v1/mail-attachments/${encodeURIComponent(attachmentId)}/content`;
  },
};
