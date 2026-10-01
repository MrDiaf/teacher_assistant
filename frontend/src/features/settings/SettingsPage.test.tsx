import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SettingsPage } from "./SettingsPage";

const disconnected = {
  connected: false,
  status: null,
  host: null,
  port: null,
  tls_mode: null,
  mailbox: null,
  username: null,
  last_checked_at: null,
  last_success_at: null,
  next_check_at: null,
  safe_error_code: null,
  safe_error: null,
  source_warning: null,
  quarantined_count: 0,
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

describe("Settings mail connection", () => {
  it("offers shared ChatGPT authentication independently of Assistant", async () => {
    const requests: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        requests.push(`${init?.method ?? "GET"} ${url}`);
        if (url.endsWith("/api/v1/ai/auth/device-code")) {
          return response(
            {
              login_id: "login-1",
              verification_url: "https://example.com/device",
              user_code: "ABCD-EFGH",
              status: "pending",
              safe_error: null,
            },
            201,
          );
        }
        if (url.endsWith("/api/v1/ai/auth")) {
          return response({
            authenticated: false,
            auth_type: null,
            email: null,
            plan_type: null,
          });
        }
        return response(disconnected);
      }),
    );

    render(<SettingsPage />);
    expect(
      await screen.findByRole("heading", { name: "ChatGPT connection" }),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Sign in with ChatGPT" }),
    );
    expect(await screen.findByText("ABCD-EFGH")).toBeInTheDocument();
    expect(requests).toContain("POST /api/v1/ai/auth/device-code");
    expect(
      requests.some((request) => request.includes("/api/v1/assistant")),
    ).toBe(false);
  });

  it("connects through the backend and never renders or persists the returned password", async () => {
    const requests: { url: string; body?: string | null }[] = [];
    const connected = {
      ...disconnected,
      connected: true,
      status: "connected",
      host: "imap.example.com",
      port: 993,
      tls_mode: "implicit_tls",
      mailbox: "INBOX",
      username: "dedicated@example.com",
      next_check_at: "2026-09-03T12:00:00Z",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
        requests.push({ url: String(input), body: init?.body?.toString() });
        if ((init?.method ?? "GET") === "PUT") return response(connected);
        return response(disconnected);
      }),
    );

    render(<SettingsPage />);
    await screen.findByRole("heading", { name: "Mail inbox" });
    fireEvent.change(screen.getByLabelText("IMAP host"), {
      target: { value: "imap.example.com" },
    });
    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "dedicated@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/^App password/), {
      target: { value: "browser-only-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Connect mailbox" }));

    expect(
      await screen.findByText(/tested and connected/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^App password/)).toHaveValue("");
    expect(document.body).not.toHaveTextContent("browser-only-secret");
    const setup = requests.find(
      (item) => item.url.endsWith("/integrations/mail") && item.body,
    );
    expect(JSON.parse(setup?.body ?? "{}").password).toBe(
      "browser-only-secret",
    );
    expect(window.localStorage.length).toBe(0);
  });

  it("shows reconnect-required health without losing the configured safe metadata", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        response({
          ...disconnected,
          status: "reconnect_required",
          host: "imap.example.com",
          port: 993,
          tls_mode: "implicit_tls",
          mailbox: "INBOX",
          username: "dedicated@example.com",
          safe_error: "Reconnect the dedicated mailbox to resume checks.",
        }),
      ),
    );
    render(<SettingsPage />);
    expect(
      await screen.findByText(/reconnect the dedicated mailbox/i),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("imap.example.com")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reconnect mailbox" }),
    ).toBeEnabled();
  });
});
