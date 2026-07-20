import { ApiError } from "../calendar/api";
import type {
  AssistantAuthStatus,
  AssistantConversation,
  AssistantConversationDetail,
  AssistantDeviceLogin,
  AssistantJob,
  AssistantProposal,
  AssistantTurn,
} from "./types";

interface ApiErrorPayload {
  message?: string;
  detail?: string | { msg?: string }[];
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
    throw new ApiError(
      payload?.message ??
        validationMessage ??
        "The assistant request could not be completed.",
      response.status,
    );
  }
  return (await response.json()) as T;
}

export const assistantApi = {
  getAuthStatus(signal?: AbortSignal) {
    return request<AssistantAuthStatus>("/assistant/auth", { signal });
  },

  startDeviceLogin() {
    return request<AssistantDeviceLogin>("/assistant/auth/device-code", {
      method: "POST",
    });
  },

  getDeviceLogin(loginId: string, signal?: AbortSignal) {
    return request<AssistantDeviceLogin>(
      `/assistant/auth/device-code/${encodeURIComponent(loginId)}`,
      { signal },
    );
  },

  logout() {
    return request<AssistantAuthStatus>("/assistant/auth", {
      method: "DELETE",
    });
  },

  listConversations(signal?: AbortSignal) {
    return request<AssistantConversation[]>("/assistant/conversations", {
      signal,
    });
  },

  createConversation(title = "Calendar conversation") {
    return request<AssistantConversation>("/assistant/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  },

  getConversation(conversationId: string, signal?: AbortSignal) {
    return request<AssistantConversationDetail>(
      `/assistant/conversations/${conversationId}`,
      { signal },
    );
  },

  sendMessage(conversationId: string, content: string) {
    return request<AssistantTurn>(
      `/assistant/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content }),
      },
    );
  },

  getJob(jobId: string) {
    return request<AssistantJob>(`/assistant/jobs/${jobId}`);
  },

  listAudit(limit = 50) {
    return request<AssistantProposal[]>(`/assistant/audit?limit=${limit}`);
  },

  retryJob(jobId: string) {
    return request<AssistantTurn>(`/assistant/jobs/${jobId}/retry`, {
      method: "POST",
    });
  },

  getProposal(proposalId: string) {
    return request<AssistantProposal>(`/assistant/proposals/${proposalId}`);
  },

  confirmProposal(proposalId: string) {
    return request<AssistantProposal>(
      `/assistant/proposals/${proposalId}/confirm`,
      { method: "POST" },
    );
  },

  rejectProposal(proposalId: string) {
    return request<AssistantProposal>(
      `/assistant/proposals/${proposalId}/reject`,
      { method: "POST" },
    );
  },

  reviseProposal(proposalId: string, content: string) {
    return request<AssistantTurn>(`/assistant/proposals/${proposalId}/revise`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },
};
