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

test("creates and manages a manual course through the UI", async ({
  page,
  request,
}) => {
  const courseCalendarResponse = await request.post("/api/v1/calendars", {
    data: {
      name: "Course E2E schedule",
      description: "Calendar linked by the course end-to-end test",
      color: "#8f6ea8",
    },
  });
  expect(courseCalendarResponse.ok()).toBeTruthy();
  const courseCalendar = (await courseCalendarResponse.json()) as {
    id: string;
  };
  const courseEventStart = new Date();
  courseEventStart.setHours(13, 0, 0, 0);
  const courseEventEnd = new Date(courseEventStart.getTime() + 60 * 60 * 1000);
  const courseEventResponse = await request.post("/api/v1/events", {
    data: {
      calendar_id: courseCalendar.id,
      title: "Course-linked E2E lecture",
      description: null,
      location: "Campus",
      start_at: courseEventStart.toISOString(),
      end_at: courseEventEnd.toISOString(),
      all_day: false,
      timezone: "Europe/Oslo",
      recurrence_rule: null,
      status: "confirmed",
    },
  });
  expect(courseEventResponse.ok()).toBeTruthy();
  const courseEvent = (await courseEventResponse.json()) as { id: string };

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

  await page.getByRole("tab", { name: "Calendar" }).click();
  await expect(
    page.getByRole("heading", { name: "No calendars linked yet" }),
  ).toBeVisible();
  const courseCalendarSidebar = page.getByRole("complementary", {
    name: "Course calendars",
  });
  await courseCalendarSidebar
    .getByLabel("Calendar to link")
    .selectOption(courseCalendar.id);
  await courseCalendarSidebar
    .getByRole("button", { name: "Link calendar" })
    .click();
  await expect(page.getByText("Course-linked E2E lecture")).toBeVisible();

  await page.getByText("Course-linked E2E lecture").click();
  const eventDialog = page.getByRole("dialog");
  await expect(eventDialog.getByLabel("Title")).toBeEnabled();
  await eventDialog.getByRole("button", { name: "Close", exact: true }).click();

  const courseCalendarResults = await new AxeBuilder({ page }).analyze();
  expectNoAccessibilityViolations(courseCalendarResults.violations);

  await courseCalendarSidebar
    .getByRole("button", { name: "Unlink Course E2E schedule" })
    .click();
  await expect(
    page.getByRole("heading", { name: "No calendars linked yet" }),
  ).toBeVisible();
  expect(
    (await request.get(`/api/v1/events/${courseEvent.id}`)).ok(),
  ).toBeTruthy();

  await courseCalendarSidebar
    .getByLabel("Calendar to link")
    .selectOption(courseCalendar.id);
  await courseCalendarSidebar
    .getByRole("button", { name: "Link calendar" })
    .click();
  await expect(page.getByText("Course-linked E2E lecture")).toBeVisible();

  await page.getByRole("tab", { name: "Materials" }).click();
  await page.getByLabel("Upload literature").setInputFiles({
    name: "database-reading.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Transactions, normalization, and indexing."),
  });
  const literature = page
    .getByRole("article")
    .filter({ hasText: "database-reading" });
  await expect(literature.getByText("Ready", { exact: true })).toBeVisible();
  await expect(literature.getByText(/1 text section extracted/)).toBeVisible();

  await page.getByLabel("Upload slides").setInputFiles({
    name: "lecture-assets.zip",
    mimeType: "application/zip",
    buffer: Buffer.from("stored unsupported source"),
  });
  const slides = page
    .getByRole("article")
    .filter({ hasText: "lecture-assets" });
  await expect(
    slides.getByText("Stored · extraction unavailable"),
  ).toBeVisible();

  await literature.getByRole("button", { name: "Delete" }).click();
  await expect(
    literature.getByText(/Other course materials are unaffected/),
  ).toBeVisible();
  await literature.getByRole("button", { name: "Delete this file" }).click();
  await expect(literature).toHaveCount(0);
  await expect(slides).toBeVisible();

  await page.getByRole("tab", { name: "Notes" }).click();
  await page.getByRole("button", { name: "Create note" }).first().click();
  const noteDialog = page.getByRole("dialog");
  await noteDialog.getByLabel("Note title").fill("Transaction isolation");
  await noteDialog
    .getByLabel("Note body")
    .fill("# Serializable\nAvoid write skew and dirty reads.");
  await noteDialog.getByRole("button", { name: "Add reference" }).click();
  await noteDialog
    .getByLabel("Slide deck 1")
    .selectOption({ label: "lecture-assets" });
  await noteDialog.getByLabel("Start slide 1").fill("3");
  await noteDialog.getByLabel("End slide 1").fill("5");
  await noteDialog.getByLabel("Reference label 1").fill("Isolation overview");
  await noteDialog.getByRole("button", { name: "Create note" }).click();

  const note = page
    .getByRole("article")
    .filter({ hasText: "Transaction isolation" });
  await expect(note.getByText("lecture-assets")).toBeVisible();
  await expect(note.getByText("Slides 3–5")).toBeVisible();
  await expect(note.getByText(/Isolation overview/)).toBeVisible();

  await page
    .getByLabel("Summary model")
    .selectOption({ value: "gpt-5.6-terra" });
  await note.getByRole("button", { name: "Generate summary" }).click();
  await expect(note.getByText("Summary failed safely")).toBeVisible();
  await expect(note.getByText("gpt-5.6-terra")).toBeVisible();
  await expect(
    note.getByText(/Linked slide text is unavailable/),
  ).toBeVisible();

  await note.getByRole("button", { name: "Edit" }).click();
  await noteDialog.getByLabel("Note title").fill("Serializable isolation");
  await noteDialog.getByRole("button", { name: "Save changes" }).click();
  await expect(
    page.getByRole("heading", { name: "Serializable isolation" }),
  ).toBeVisible();

  const notesResults = await new AxeBuilder({ page }).analyze();
  expectNoAccessibilityViolations(notesResults.violations);

  const updatedNote = page
    .getByRole("article")
    .filter({ hasText: "Serializable isolation" });
  await updatedNote.getByRole("button", { name: "Delete" }).click();
  await expect(
    updatedNote.getByText(/Slide files are unaffected/),
  ).toBeVisible();
  await updatedNote.getByRole("button", { name: "Delete note" }).click();
  await expect(
    page.getByRole("heading", { name: "Start your course notebook" }),
  ).toBeVisible();

  await page
    .locator(".course-detail-actions")
    .getByRole("button", { name: "Delete", exact: true })
    .click();
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
  expect(
    (await request.get(`/api/v1/calendars/${courseCalendar.id}`)).ok(),
  ).toBeTruthy();
  expect(
    (await request.get(`/api/v1/events/${courseEvent.id}`)).ok(),
  ).toBeTruthy();
});

test("explains a sanitized course-material error without exposing private input", async ({
  page,
  request,
}) => {
  const courseResponse = await request.post("/api/v1/courses", {
    data: {
      name: "Diagnostic E2E course",
      course_code: "DIAG101",
      description: "Exercises the sanitized error Assistant flow.",
      term: "Autumn 2026",
      color: "#29584c",
    },
  });
  expect(courseResponse.ok()).toBeTruthy();
  const course = (await courseResponse.json()) as { id: string };

  await page.route(
    `**/api/v1/courses/${course.id}/sources?**`,
    async (route) => {
      await route.fulfill({
        status: 413,
        contentType: "application/json",
        body: JSON.stringify({
          error_id: "e2e-sanitized-error",
          code: "course_source_file_too_large",
          message: "The course file exceeds the 25 MB upload limit.",
          details: {
            content_type: "application/pdf",
            maximum_size_mb: 25,
          },
          request_id: "e2e-request",
        }),
      });
    },
  );
  await page.route(
    "**/api/v1/assistant/errors/e2e-sanitized-error/explain",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          error_id: "e2e-sanitized-error",
          request_id: "e2e-request",
          model: "gpt-5.6-sol",
          explained_at: new Date().toISOString(),
          plain_explanation:
            "The selected file is larger than the upload limit.",
          likely_cause: "Its size exceeds 25 MB.",
          input_fixes: ["Choose a smaller or compressed PDF."],
          application_improvements: [
            "Show the file-size limit beside the picker.",
          ],
          retry_is_safe: true,
        }),
      });
    },
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Courses" }).click();
  await page
    .getByRole("button", { name: "Open Diagnostic E2E course" })
    .click();
  await page.getByRole("tab", { name: "Materials" }).click();
  await page.getByLabel("Upload literature").setInputFiles({
    name: "private-course-handout.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("private content must not enter the diagnostic report"),
  });
  await expect(
    page.getByText("The course file exceeds the 25 MB upload limit."),
  ).toBeVisible();

  await page
    .getByRole("button", { name: "Ask Assistant about this error" })
    .click();
  const explanation = page.getByRole("region", {
    name: "Assistant error explanation",
  });
  await expect(explanation).toContainText(
    "Choose a smaller or compressed PDF.",
  );
  await expect(explanation).toContainText(
    "Show the file-size limit beside the picker.",
  );
  await expect(page.getByText("private content must not enter")).toHaveCount(0);

  const accessibility = await new AxeBuilder({ page }).analyze();
  expectNoAccessibilityViolations(accessibility.violations);
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
