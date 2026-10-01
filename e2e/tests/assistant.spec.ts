import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const conversation = {
  id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  title: "Focused Assistant conversation",
  created_at: "2026-09-30T08:00:00Z",
  updated_at: "2026-09-30T08:00:00Z",
};

test("mounts the real Assistant UI with bounded fixture capabilities", async ({
  page,
}) => {
  const seen: string[] = [];
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    seen.push(`${request.method()} ${pathname}`);
    if (pathname === "/api/v1/ai/models") {
      await route.fulfill({
        json: {
          default_model: "gpt-5.6-terra",
          models: [{ id: "gpt-5.6-terra", label: "GPT-5.6 Terra" }],
        },
      });
      return;
    }
    if (pathname === "/api/v1/assistant/auth") {
      await route.fulfill({
        json: {
          authenticated: true,
          auth_type: "chatgpt",
          email: "owner@example.test",
          plan_type: "plus",
        },
      });
      return;
    }
    if (pathname === "/api/v1/assistant/conversations") {
      await route.fulfill({ json: [conversation] });
      return;
    }
    if (pathname === `/api/v1/assistant/conversations/${conversation.id}`) {
      await route.fulfill({
        json: {
          ...conversation,
          messages: [],
          jobs: [],
          proposals: [],
        },
      });
      return;
    }
    if (!pathname.startsWith("/api/v1/assistant")) {
      await route.fallback();
      return;
    }
    throw new Error(
      `Fixture rejected undeclared Assistant request: ${request.method()} ${pathname}`,
    );
  });

  await page.goto("/");
  await page.evaluate(() => {
    window.localStorage.removeItem("teacher-assistant.ui-state.v1");
  });
  await page.reload();
  await page.getByRole("button", { name: "Assistant" }).click();

  await expect(page.getByRole("heading", { name: "Assistant" })).toBeVisible();
  await expect(page.getByText("owner@example.test")).toBeVisible();
  const composer = page.getByLabel("Message the Assistant");
  await composer.fill("  focused draft survives reload  ");
  await page.reload();
  await expect(page.getByLabel("Message the Assistant")).toHaveValue(
    "  focused draft survives reload  ",
  );

  const accessibility = await new AxeBuilder({ page })
    .include(".assistant-page")
    .analyze();
  expect(
    accessibility.violations.map((violation) => ({
      id: violation.id,
      targets: violation.nodes.map((node) => node.target.join(" ")),
    })),
  ).toEqual([]);
  expect(seen).toContain("GET /api/v1/assistant/conversations");
  expect(seen).toContain("GET /api/v1/assistant/auth");
  expect(seen).toContain("GET /api/v1/ai/models");
});
