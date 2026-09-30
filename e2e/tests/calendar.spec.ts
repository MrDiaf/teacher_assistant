import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    window.localStorage.removeItem("teacher-assistant.ui-state.v1");
  });
});

test("creates, edits, filters, changes views, and undoes its own event", async ({
  page,
  request,
}) => {
  const calendarResponse = await request.post("/api/v1/calendars", {
    data: {
      name: "Focused calendar E2E",
      description: "Independent Calendar workflow test",
      color: "#c58b2a",
    },
  });
  expect(calendarResponse.ok()).toBeTruthy();

  await page.reload();
  await expect(
    page.getByRole("checkbox", { name: "Show Focused calendar E2E" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Create event", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Title").fill("Focused calendar planning");
  await dialog.getByRole("button", { name: "Create event" }).click();
  await expect(page.getByText("Focused calendar planning")).toBeVisible();

  await page.getByRole("button", { name: "Week", exact: true }).click();
  await page.getByRole("button", { name: "Day", exact: true }).click();
  await page.getByRole("button", { name: "Month", exact: true }).click();
  await page
    .getByPlaceholder("Search title, description, or location")
    .fill("focused");
  await expect(
    page
      .locator(".calendar-search-results")
      .getByText("Focused calendar planning"),
  ).toBeVisible();
  await page
    .getByPlaceholder("Search title, description, or location")
    .fill("");

  await page
    .locator(".month-event")
    .filter({ hasText: "Focused calendar planning" })
    .click();
  await dialog.getByLabel("Title").fill("Edited focused planning");
  await dialog.getByRole("button", { name: "Save changes" }).click();
  await expect(
    page.locator(".month-event").filter({ hasText: "Edited focused planning" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(
    page
      .locator(".month-event")
      .filter({ hasText: "Focused calendar planning" }),
  ).toBeVisible();

  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
});

test("seeds and verifies a protected event without prior test state", async ({
  page,
  request,
}) => {
  const calendarResponse = await request.post("/api/v1/calendars", {
    data: {
      name: "Protected focused E2E",
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
      title: "Protected focused event",
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
  expect(
    (
      await request.patch(`/api/v1/calendars/${calendar.id}`, {
        data: { is_read_only: true },
      })
    ).ok(),
  ).toBeTruthy();

  await page.goto("/");
  await page.getByText("Protected focused event").click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByText(/belongs to a read-only calendar/),
  ).toBeVisible();
  await expect(dialog.getByLabel("Title")).toBeDisabled();
  await expect(
    dialog.getByRole("button", { name: "Save changes" }),
  ).toHaveCount(0);
});
