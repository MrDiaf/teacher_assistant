import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InboxPage } from "./InboxPage";

const item = {
  id: "11111111-1111-4111-8111-111111111111",
  subject: "Forwarded lecture update",
  sender_name: "School Office",
  sender_address: "office@example.edu",
  recipients: ["dedicated@example.com"],
  source_date: "2026-09-03T07:00:00Z",
  ingested_at: "2026-09-03T07:01:00Z",
  attachment_count: 1,
  omitted_attachment_count: 1,
  is_read: false,
  is_archived: false,
  forwarded_unverified: true,
  source_label: "Mail",
};

const detail = {
  ...item,
  message_id: "<one@example.edu>",
  in_reply_to: null,
  thread_references: [],
  body_text: "Safe body text",
  body_html: '<img src="https://tracker.example/pixel"><script>bad()</script>',
  addresses: [
    {
      kind: "from",
      display_name: "School Office",
      address: "office@example.edu",
      position: 0,
    },
    {
      kind: "to",
      display_name: null,
      address: "dedicated@example.com",
      position: 0,
    },
  ],
  attachments: [
    {
      id: "22222222-2222-4222-8222-222222222222",
      original_filename: "schedule.pdf",
      mime_type: "application/pdf",
      file_size: 12,
      status: "stored",
      omission_reason: null,
    },
    {
      id: "33333333-3333-4333-8333-333333333333",
      original_filename: "large.zip",
      mime_type: "application/zip",
      file_size: 0,
      status: "omitted",
      omission_reason: "The attachment exceeded the configured size limit.",
    },
  ],
};

function response(body: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Inbox", () => {
  it("loads safe Mail provenance, marks locally read, and never injects HTML mail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        if (
          url.endsWith(`/inbox/${item.id}`) &&
          (init?.method ?? "GET") === "GET"
        ) {
          return response(detail);
        }
        if (url.endsWith(`/inbox/${item.id}`) && init?.method === "PATCH") {
          return response({ ...detail, is_read: true });
        }
        return response([item]);
      }),
    );
    render(<InboxPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: /School Office/i }),
    );

    expect(
      await screen.findByRole("heading", { name: item.subject }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/forwarded content unverified/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Safe body text")).toBeInTheDocument();
    expect(
      screen.getByText(/HTML mail converted to safe passive text/i),
    ).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("img")).toBeNull();
    expect(document.body).not.toHaveTextContent("tracker.example");
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute(
      "href",
      "/api/v1/mail-attachments/22222222-2222-4222-8222-222222222222/content",
    );
    expect(
      screen.getByText(/Omitted — The attachment exceeded/i),
    ).toBeInTheDocument();
  });

  it("requires browser confirmation before deleting one local message", async () => {
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        if (
          url.endsWith(`/inbox/${item.id}`) &&
          (init?.method ?? "GET") === "GET"
        )
          return response(detail);
        if (url.endsWith(`/inbox/${item.id}`) && init?.method === "PATCH")
          return response({ ...detail, is_read: true });
        if (url.endsWith(`/inbox/${item.id}`) && init?.method === "DELETE")
          return response(null, 204);
        return response([item]);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<InboxPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: /School Office/i }),
    );
    fireEvent.click(
      await screen.findByRole("button", { name: "Delete locally" }),
    );
    expect(
      fetchMock.mock.calls.some(([, init]) => init?.method === "DELETE"),
    ).toBe(false);

    vi.mocked(window.confirm).mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", { name: "Delete locally" }));
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([, init]) => init?.method === "DELETE"),
      ).toBe(true),
    );
  });
});
