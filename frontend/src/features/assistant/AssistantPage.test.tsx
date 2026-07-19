import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../../App";
import type {
  AssistantConversation,
  AssistantJob,
  AssistantMessage,
} from "./types";

const now = new Date().toISOString();
const conversation: AssistantConversation = {
  id: "conversation-1",
  title: "Calendar conversation",
  created_at: now,
  updated_at: now,
};
const ownerMessage: AssistantMessage = {
  id: "message-owner",
  conversation_id: conversation.id,
  role: "owner",
  content: "What do I have tomorrow?",
  job_id: null,
  created_at: now,
};
const assistantMessage: AssistantMessage = {
  id: "message-assistant",
  conversation_id: conversation.id,
  role: "assistant",
  content: "You have a planning session from 10:00 to 11:00.",
  job_id: "job-1",
  created_at: now,
};
const connectedAuth = {
  authenticated: true,
  auth_type: "chatgpt",
  email: "owner@example.test",
  plan_type: "plus",
};

function job(
  status: AssistantJob["status"],
  safeError: string | null = null,
): AssistantJob {
  return {
    id: "job-1",
    conversation_id: conversation.id,
    owner_message_id: ownerMessage.id,
    status,
    safe_error: safeError,
    created_at: now,
    updated_at: now,
  };
}

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("AssistantPage", () => {
  it("sends an owner message through FastAPI and displays the validated answer", async () => {
    let messages: AssistantMessage[] = [];
    const renamedConversation = {
      ...conversation,
      title: "What do I have tomorrow?",
    };
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        if (url.endsWith("/api/v1/assistant/auth") && method === "GET") {
          return response(connectedAuth);
        }
        if (
          url.endsWith("/api/v1/assistant/conversations") &&
          method === "GET"
        ) {
          return response([]);
        }
        if (
          url.endsWith("/api/v1/assistant/conversations") &&
          method === "POST"
        ) {
          return response(conversation, 201);
        }
        if (
          url.endsWith(
            `/api/v1/assistant/conversations/${conversation.id}/messages`,
          ) &&
          method === "POST"
        ) {
          messages = [ownerMessage, assistantMessage];
          return response({
            conversation: renamedConversation,
            owner_message: ownerMessage,
            assistant_message: assistantMessage,
            job: job("completed"),
          });
        }
        if (
          url.endsWith(`/api/v1/assistant/conversations/${conversation.id}`) &&
          method === "GET"
        ) {
          return response({
            ...renamedConversation,
            messages,
            jobs: messages.length ? [job("completed")] : [],
          });
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Assistant" }));
    expect(await screen.findByText("Read-only mode")).toBeInTheDocument();
    expect(
      screen.getByText("What would you like to know?"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Message the calendar assistant"), {
      target: { value: "What do I have tomorrow?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(
      await screen.findByText(
        "You have a planning session from 10:00 to 11:00.",
      ),
    ).toBeInTheDocument();
    const messageCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        String(url).endsWith(
          `/api/v1/assistant/conversations/${conversation.id}/messages`,
        ) && init?.method === "POST",
    );
    expect(JSON.parse(String(messageCall?.[1]?.body))).toEqual({
      content: "What do I have tomorrow?",
    });
  });

  it("shows a safe failed-job state and retries the same stored message", async () => {
    let retryCompleted = false;
    let messageSent = false;
    const failedJob = job("failed", "Codex is temporarily unavailable.");
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        if (url.endsWith("/api/v1/assistant/auth") && method === "GET") {
          return response(connectedAuth);
        }
        if (
          url.endsWith("/api/v1/assistant/conversations") &&
          method === "GET"
        ) {
          return response([conversation]);
        }
        if (
          url.endsWith(`/api/v1/assistant/conversations/${conversation.id}`) &&
          method === "GET"
        ) {
          return response({
            ...conversation,
            messages: retryCompleted
              ? [ownerMessage, assistantMessage]
              : messageSent
                ? [ownerMessage]
                : [],
            jobs: messageSent
              ? [retryCompleted ? job("completed") : failedJob]
              : [],
          });
        }
        if (
          url.endsWith(
            `/api/v1/assistant/conversations/${conversation.id}/messages`,
          ) &&
          method === "POST"
        ) {
          messageSent = true;
          return response({
            conversation,
            owner_message: ownerMessage,
            assistant_message: null,
            job: failedJob,
          });
        }
        if (
          url.endsWith("/api/v1/assistant/jobs/job-1/retry") &&
          method === "POST"
        ) {
          retryCompleted = true;
          return response({
            conversation,
            owner_message: ownerMessage,
            assistant_message: assistantMessage,
            job: job("completed"),
          });
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Assistant" }));
    await screen.findByText("What would you like to know?");
    fireEvent.change(screen.getByLabelText("Message the calendar assistant"), {
      target: { value: ownerMessage.content },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(
      await screen.findByText("Codex is temporarily unavailable."),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry safely" }));
    expect(
      await screen.findByText(
        "You have a planning session from 10:00 to 11:00.",
      ),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) =>
            String(url).endsWith("/api/v1/assistant/jobs/job-1/retry") &&
            init?.method === "POST",
        ),
      ).toBe(true),
    );
  });

  it("offers a safe ChatGPT subscription device-login link when signed out", async () => {
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        if (url.endsWith("/api/v1/assistant/auth") && method === "GET") {
          return response({
            authenticated: false,
            auth_type: null,
            email: null,
            plan_type: null,
          });
        }
        if (
          url.endsWith("/api/v1/assistant/conversations") &&
          method === "GET"
        ) {
          return response([]);
        }
        if (
          url.endsWith("/api/v1/assistant/auth/device-code") &&
          method === "POST"
        ) {
          return response(
            {
              login_id: "login-123",
              verification_url: "https://auth.openai.com/codex/device",
              user_code: "ABCD-EFGH",
              status: "pending",
              safe_error: null,
            },
            201,
          );
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Assistant" }));
    expect(
      await screen.findByRole("heading", {
        name: "Use your ChatGPT subscription",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Message the calendar assistant"),
    ).toBeDisabled();

    fireEvent.click(
      screen.getByRole("button", { name: "Sign in with ChatGPT" }),
    );

    const signInLink = await screen.findByRole("link", {
      name: "Open OpenAI sign-in",
    });
    expect(signInLink).toHaveAttribute(
      "href",
      "https://auth.openai.com/codex/device",
    );
    expect(screen.getByLabelText("ChatGPT device code")).toHaveTextContent(
      "ABCD-EFGH",
    );
    expect(
      screen.getByText(/An API key is not required\./),
    ).toBeInTheDocument();
  });
});
