import { parseApiResponse } from "../../platform/api";
import type {
  AiAuthStatus,
  AiDeviceLogin,
  AiModelList,
  DiagnosticExplanation,
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
    "The private AI request could not be completed.",
  );
}

export async function getAiModels(signal?: AbortSignal): Promise<AiModelList> {
  return request<AiModelList>("/ai/models", { signal });
}

export const aiApi = {
  getAuthStatus(signal?: AbortSignal) {
    return request<AiAuthStatus>("/ai/auth", { signal });
  },

  startDeviceLogin() {
    return request<AiDeviceLogin>("/ai/auth/device-code", { method: "POST" });
  },

  getDeviceLogin(loginId: string, signal?: AbortSignal) {
    return request<AiDeviceLogin>(
      `/ai/auth/device-code/${encodeURIComponent(loginId)}`,
      { signal },
    );
  },

  logout() {
    return request<AiAuthStatus>("/ai/auth", { method: "DELETE" });
  },

  explainError(errorId: string, model?: string) {
    return request<DiagnosticExplanation>(
      `/diagnostics/errors/${encodeURIComponent(errorId)}/explain`,
      {
        method: "POST",
        body: JSON.stringify(model ? { model } : {}),
      },
    );
  },
};
