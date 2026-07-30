import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { AxeResults } from "axe-core";

test.describe.configure({ mode: "serial" });

function expectNoAccessibilityViolations(violations: AxeResults["violations"]) {
  expect(
    violations.map((violation) => ({
      id: violation.id,
      targets: violation.nodes.map((node) => node.target.join(" ")),
    })),
  ).toEqual([]);
}

test("creates, edits, and undoes a calendar event through the UI", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Set up calendar" }).click();
  await expect(
    page.getByRole("checkbox", { name: "Show Personal" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Create event", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Title").fill("End-to-end planning");
  await dialog.getByRole("button", { name: "Create event" }).click();
  await expect(page.getByText("End-to-end planning")).toBeVisible();

  await page.getByText("End-to-end planning").click();
  await dialog.getByLabel("Title").fill("Edited end-to-end planning");
  await dialog.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Edited end-to-end planning")).toBeVisible();

  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(page.getByText("End-to-end planning")).toBeVisible();
});

test("keeps a protected event visible but immutable", async ({
  page,
  request,
}) => {
  const calendarResponse = await request.post("/api/v1/calendars", {
    data: {
      name: "Protected E2E",
      description: "Read-only test",
      color: "#5b7fa3",
    },
  });
  expect(calendarResponse.ok()).toBeTruthy();
  const calendar = (await calendarResponse.json()) as { id: string };
  const start = new Date();
  start.setDate(start.getDate() + 1);
  start.setHours(10, 0, 0, 0);
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  const eventResponse = await request.post("/api/v1/events", {
    data: {
      calendar_id: calendar.id,
      title: "Protected E2E event",
      description: null,
      location: null,
      start_at: start.toISOString(),
      end_at: end.toISOString(),
      all_day: false,
      timezone: "Europe/Oslo",
      recurrence_rule: null,
      status: "confirmed",
    },
  });
  expect(eventResponse.ok()).toBeTruthy();
  const protectionResponse = await request.patch(
    `/api/v1/calendars/${calendar.id}`,
    { data: { is_read_only: true } },
  );
  expect(protectionResponse.ok()).toBeTruthy();

  await page.goto("/");
  await page.getByText("Protected E2E event").click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByText(/belongs to a read-only calendar/),
  ).toBeVisible();
  await expect(dialog.getByLabel("Title")).toBeDisabled();
  await expect(
    dialog.getByRole("button", { name: "Save changes" }),
  ).toHaveCount(0);
});

test("creates and manages a manual course through the UI", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Courses" }).click();
  await expect(page.getByRole("heading", { name: "Courses" })).toBeVisible();

  await page.getByRole("button", { name: "Create course" }).first().click();
  const courseDialog = page.getByRole("dialog");
  await courseDialog.getByLabel("Course name").fill("End-to-end databases");
  await courseDialog.getByLabel("Course code").fill("E2E101");
  await courseDialog.getByLabel("Term").fill("Autumn 2026");
  await courseDialog
    .getByLabel("Description")
    .fill("A course created by the end-to-end test.");
  await courseDialog.getByRole("button", { name: "Create course" }).click();

  await page.getByRole("button", { name: "Open End-to-end databases" }).click();
  await expect(
    page.getByRole("heading", { name: "End-to-end databases" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Edit course" }).click();
  await courseDialog
    .getByLabel("Course name")
    .fill("Edited end-to-end databases");
  await courseDialog.getByRole("button", { name: "Save changes" }).click();
  await expect(
    page.getByRole("heading", { name: "Edited end-to-end databases" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Archive" }).click();
  await expect(page.getByRole("button", { name: "Restore" })).toBeVisible();
  await page.getByRole("button", { name: "Restore" }).click();
  await expect(page.getByRole("button", { name: "Archive" })).toBeVisible();

  await page.getByRole("button", { name: "Delete" }).click();
  const deleteDialog = page.getByRole("alertdialog");
  await expect(
    deleteDialog.getByText(/Calendars and calendar events are never deleted/),
  ).toBeVisible();
  await deleteDialog
    .getByRole("button", { name: "Delete course", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Create your first course" }),
  ).toBeVisible();
});

test("passes an automated accessibility scan and supports subscription sign-in", async ({
  page,
}) => {
  await page.goto("/");
  const calendarResults = await new AxeBuilder({ page }).analyze();
  expectNoAccessibilityViolations(calendarResults.violations);

  await page.getByRole("button", { name: "Assistant" }).click();
  await expect(
    page.getByRole("heading", { name: "Use your ChatGPT subscription" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Sign in with ChatGPT" }),
  ).toBeVisible();
  const assistantResults = await new AxeBuilder({ page }).analyze();
  expectNoAccessibilityViolations(assistantResults.violations);
});

test("keeps navigation usable at a phone viewport without page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(navigation).toBeVisible();
  await page.getByRole("button", { name: "Assistant" }).click();
  await expect(page.getByRole("heading", { name: "Assistant" })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
});
