import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../../App";
import type {
  AssistantConversation,
  AssistantJob,
  AssistantMessage,
  AssistantProposal,
} from "./types";

vi.mock("../ai/api", () => ({
  getAiModels: vi.fn(async () => ({
    default_model: "gpt-5.6-sol",
    models: [
      { id: "gpt-5.6-sol", label: "GPT-5.6 Sol · flagship" },
      { id: "gpt-5.6-terra", label: "GPT-5.6 Terra · balanced" },
    ],
  })),
}));

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
  citations: [],
  job_id: null,
  created_at: now,
};
const assistantMessage: AssistantMessage = {
  id: "message-assistant",
  conversation_id: conversation.id,
  role: "assistant",
  content: "You have a planning session from 10:00 to 11:00.",
  citations: [],
  job_id: "job-1",
  created_at: now,
};
const connectedAuth = {
  authenticated: true,
  auth_type: "chatgpt",
  email: "owner@example.test",
  plan_type: "plus",
};

const awaitingProposal: AssistantProposal = {
  id: "proposal-1",
  job_id: "job-1",
  conversation_id: conversation.id,
  status: "awaiting_confirmation",
  summary: "Move the planning session",
  batch_position: 1,
  batch_count: 1,
  actions: [
    {
      operation: "update_event",
      calendar_id: "calendar-1",
      event_id: "event-1",
    },
  ],
  review_items: [
    {
      operation: "update_event",
      title: "Update event “Planning session”",
      calendar_id: "calendar-1",
      calendar_name: "Personal",
      event_id: "event-1",
      event_title: "Planning session",
      previous: { start_at: "2026-07-20T08:00:00Z" },
      proposed: { start_at: "2026-07-20T10:00:00Z" },
      recurrence_scope: null,
      occurrence_start_at: null,
      affected_events: 1,
      warnings: [],
    },
  ],
  warnings: [],
  affected_events: 1,
  expires_at: "2026-07-20T12:00:00Z",
  confirmed_at: null,
  rejected_at: null,
  executed_at: null,
  result: null,
  safe_error: null,
  created_at: now,
  updated_at: now,
  action_records: [
    {
      id: "action-1",
      position: 0,
      operation: "update_event",
      target_calendar_id: "calendar-1",
      target_event_id: "event-1",
      requested_at: now,
      confirmed_at: null,
      executed_at: null,
      result: null,
      safe_error: null,
    },
  ],
};

function job(
  status: AssistantJob["status"],
  safeError: string | null = null,
  overrides: Partial<AssistantJob> = {},
): AssistantJob {
  return {
    id: "job-1",
    conversation_id: conversation.id,
    owner_message_id: ownerMessage.id,
    status,
    model: "gpt-5.6-sol",
    safe_error: safeError,
    safe_error_code: safeError ? "assistant_unavailable" : null,
    safe_error_details: {},
    diagnostic_error_id: null,
    created_at: now,
    updated_at: now,
    ...overrides,
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
    const citedAssistantMessage: AssistantMessage = {
      ...assistantMessage,
      citations: [
        {
          course_id: "course-1",
          course_name: "Datasekretess",
          note_id: "note-1",
          note_title: "Normalization",
          source_id: "source-1",
          source_name: "Lecture 4",
          slide_number: 12,
        },
      ],
    };
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
          messages = [ownerMessage, citedAssistantMessage];
          return response({
            conversation: renamedConversation,
            owner_message: ownerMessage,
            assistant_message: citedAssistantMessage,
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
    expect(await screen.findByText("Confirmation mode")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Assistant" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      screen.getByRole("link", { name: "Skip to main content" }),
    ).toHaveAttribute("href", "#main-content");
    expect(
      screen.getByText("What would you like to know?"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Message the Assistant"), {
      target: { value: "What do I have tomorrow?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(
      await screen.findByText(
        "You have a planning session from 10:00 to 11:00.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: "Course note citations" }),
    ).toHaveTextContent("Datasekretess · Normalization · Lecture 4, slide 12");
    const messageCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        String(url).endsWith(
          `/api/v1/assistant/conversations/${conversation.id}/messages`,
        ) && init?.method === "POST",
    );
    expect(JSON.parse(String(messageCall?.[1]?.body))).toEqual({
      content: "What do I have tomorrow?",
      model: "gpt-5.6-sol",
    });
  });

  it("shows a safe failed-job state and retries the same stored message", async () => {
    let retryCompleted = false;
    let messageSent = false;
    const failedJob = job(
      "failed",
      "The assistant's reply did not match the required safe response format, so the backend rejected it before saving an answer or changing calendar data.",
      {
        safe_error_code: "invalid_assistant_response",
        safe_error_details: {
          failure_stage: "validating",
          validation_stage: "response_schema",
          reason:
            "The response JSON did not match the required assistant answer schema.",
          validation_errors: [
            {
              field: "proposal.actions.0.operation",
              message: "Input tag 'delete_calendar' is not supported.",
              type: "union_tag_invalid",
            },
          ],
          owner_actions: [
            "Retry once. The retry includes this validation feedback so the assistant can correct its response format.",
          ],
          developer_actions: [
            "Inspect the validation stage and field issues below.",
          ],
        },
        diagnostic_error_id: "diagnostic-error-1",
      },
    );
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
    fireEvent.change(screen.getByLabelText("Message the Assistant"), {
      target: { value: ownerMessage.content },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(
      await screen.findByText("The reply was blocked for safety"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "The response JSON did not match the required assistant answer schema.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Retry once. The retry includes this validation feedback/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Ask Assistant about this error" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByText("Developer details"));
    expect(screen.getByText("invalid_assistant_response")).toBeInTheDocument();
    expect(screen.getByText("response_schema")).toBeInTheDocument();
    expect(screen.getByText(/delete_calendar/)).toBeInTheDocument();
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

  it("shows a change review and executes it only after confirmation", async () => {
    const completedProposal: AssistantProposal = {
      ...awaitingProposal,
      status: "completed",
      confirmed_at: now,
      executed_at: now,
      result: { actions: [{ status: "completed" }] },
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
          return response([conversation]);
        }
        if (
          url.endsWith(`/api/v1/assistant/conversations/${conversation.id}`) &&
          method === "GET"
        ) {
          return response({
            ...conversation,
            messages: [ownerMessage, assistantMessage],
            jobs: [job("awaiting_confirmation")],
            proposals: [awaitingProposal],
          });
        }
        if (
          url.endsWith(
            `/api/v1/assistant/proposals/${awaitingProposal.id}/confirm`,
          ) &&
          method === "POST"
        ) {
          return response(completedProposal);
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Assistant" }));
    expect(
      await screen.findByRole("region", {
        name: "Calendar proposal: Move the planning session",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(screen.getByText("1 affected event")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revise" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Confirm changes" }));

    expect(
      await screen.findByText(
        "Confirmed and completed by the calendar service.",
      ),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith(
            `/api/v1/assistant/proposals/${awaitingProposal.id}/confirm`,
          ) && init?.method === "POST",
      ),
    ).toBe(true);
  });

  it("shows linked batches together and confirms each batch separately", async () => {
    const firstBatch: AssistantProposal = {
      ...awaitingProposal,
      summary: "Create events 1–10",
      batch_count: 2,
    };
    const secondBatch: AssistantProposal = {
      ...awaitingProposal,
      id: "proposal-2",
      summary: "Create events 11–20",
      batch_position: 2,
      batch_count: 2,
      action_records: awaitingProposal.action_records.map((record) => ({
        ...record,
        id: "action-2",
      })),
    };
    const completedFirstBatch: AssistantProposal = {
      ...firstBatch,
      status: "completed",
      confirmed_at: now,
      executed_at: now,
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
          return response([conversation]);
        }
        if (
          url.endsWith(`/api/v1/assistant/conversations/${conversation.id}`) &&
          method === "GET"
        ) {
          return response({
            ...conversation,
            messages: [ownerMessage, assistantMessage],
            jobs: [job("awaiting_confirmation")],
            proposals: [firstBatch, secondBatch],
          });
        }
        if (
          url.endsWith(
            `/api/v1/assistant/proposals/${firstBatch.id}/confirm`,
          ) &&
          method === "POST"
        ) {
          return response(completedFirstBatch);
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Assistant" }));
    const plan = await screen.findByRole("region", {
      name: "Linked calendar plan",
    });
    expect(within(plan).getByText(/2 events across 2/)).toBeInTheDocument();
    expect(screen.getByText(/Batch 1 of 2/)).toBeInTheDocument();
    expect(screen.getByText(/Batch 2 of 2/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Confirm batch 1" }));

    expect(
      await screen.findByText(
        "Confirmed and completed by the calendar service.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Confirm batch 2" }),
    ).toBeInTheDocument();
  });

  it("loads persistent proposal activity and exposes action timestamps", async () => {
    const completedProposal: AssistantProposal = {
      ...awaitingProposal,
      status: "completed",
      confirmed_at: now,
      executed_at: now,
      action_records: awaitingProposal.action_records.map((record) => ({
        ...record,
        confirmed_at: now,
        executed_at: now,
      })),
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
          return response([conversation]);
        }
        if (
          url.endsWith(`/api/v1/assistant/conversations/${conversation.id}`) &&
          method === "GET"
        ) {
          return response({
            ...conversation,
            messages: [ownerMessage, assistantMessage],
            jobs: [job("completed")],
            proposals: [completedProposal],
          });
        }
        if (
          url.endsWith("/api/v1/assistant/audit?limit=50") &&
          method === "GET"
        ) {
          return response([completedProposal]);
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Assistant" }));
    await screen.findByText("Move the planning session");
    fireEvent.click(screen.getByRole("tab", { name: "Activity" }));

    expect(await screen.findByText(/completed ·/i)).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", {
        name: /Move the planning session completed/i,
      }),
    );
    const auditDetails = (await screen.findByText("Audit details")).closest(
      "details",
    )!;
    fireEvent.click(within(auditDetails).getByText("Audit details"));
    expect(within(auditDetails).getByText(/Requested/)).toBeInTheDocument();
    expect(within(auditDetails).getByText(/Confirmed/)).toBeInTheDocument();
    expect(within(auditDetails).getByText(/Executed/)).toBeInTheDocument();
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
    expect(screen.getByLabelText("Message the Assistant")).toBeDisabled();

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
