import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SettingsPage } from "./SettingsPage";
import { RegisteredSettingsPanelsProvider } from "./settingsPanelHost";

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Settings host", () => {
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
        return response({
          authenticated: false,
          auth_type: null,
          email: null,
          plan_type: null,
        });
      }),
    );

    render(
      <RegisteredSettingsPanelsProvider panels={[]}>
        <SettingsPage />
      </RegisteredSettingsPanelsProvider>,
    );
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

  it("renders registered panels without knowing their business behavior", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        response({
          authenticated: false,
          auth_type: null,
          email: null,
          plan_type: null,
        }),
      ),
    );

    function FixturePanel() {
      return (
        <section aria-label="Fixture contribution">Fixture content</section>
      );
    }

    render(
      <RegisteredSettingsPanelsProvider
        panels={[
          {
            id: "fixture",
            label: "Fixture",
            moduleId: "fixture",
            order: 1,
            component: FixturePanel,
          },
        ]}
      >
        <SettingsPage />
      </RegisteredSettingsPanelsProvider>,
    );

    expect(
      screen.getByRole("region", { name: "Fixture contribution" }),
    ).toHaveTextContent("Fixture content");
  });
});
