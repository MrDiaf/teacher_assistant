import { parseApiResponse } from "../../platform/api";
import type {
  AssistantAuthStatus,
  AssistantConversation,
  AssistantConversationDetail,
  AssistantDeviceLogin,
  DiagnosticExplanation,
  AssistantJob,
  AssistantProposal,
  AssistantTurn,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  return parseApiResponse<T>(
    response,
    "The assistant request could not be completed.",
  );
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

  sendMessage(
    conversationId: string,
    content: string,
    model: string,
    signal?: AbortSignal,
  ) {
    return request<AssistantTurn>(
      `/assistant/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content, model }),
        signal,
      },
    );
  },

  getJob(jobId: string) {
    return request<AssistantJob>(`/assistant/jobs/${jobId}`);
  },

  listAudit(limit = 50, signal?: AbortSignal) {
    return request<AssistantProposal[]>(`/assistant/audit?limit=${limit}`, {
      signal,
    });
  },

  retryJob(jobId: string, signal?: AbortSignal) {
    return request<AssistantTurn>(`/assistant/jobs/${jobId}/retry`, {
      method: "POST",
      signal,
    });
  },

  cancelConversation(conversationId: string) {
    return request<AssistantJob>(
      `/assistant/conversations/${conversationId}/cancel`,
      { method: "POST" },
    );
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

  reviseProposal(
    proposalId: string,
    content: string,
    model: string,
    signal?: AbortSignal,
  ) {
    return request<AssistantTurn>(`/assistant/proposals/${proposalId}/revise`, {
      method: "POST",
      body: JSON.stringify({ content, model }),
      signal,
    });
  },

  explainError(errorId: string, model?: string) {
    return request<DiagnosticExplanation>(
      `/assistant/errors/${encodeURIComponent(errorId)}/explain`,
      {
        method: "POST",
        body: JSON.stringify(model ? { model } : {}),
      },
    );
  },
};
