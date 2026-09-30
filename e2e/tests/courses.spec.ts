import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";
import type { AxeResults } from "axe-core";

import { multiPagePdfFixture } from "./pdf-fixture.js";

// Every scenario seeds its own course through the API and removes what it
// created, so each one runs alone, in any order, and in the focused host.
const createdCourseIds = new Set<string>();
const createdCalendarIds = new Set<string>();

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    window.localStorage.removeItem("teacher-assistant.ui-state.v1");
  });
});

test.afterEach(async ({ request }) => {
  for (const courseId of createdCourseIds) {
    await request.delete(`/api/v1/courses/${courseId}`);
  }
  createdCourseIds.clear();
  for (const calendarId of createdCalendarIds) {
    await request.delete(`/api/v1/calendars/${calendarId}`);
  }
  createdCalendarIds.clear();
});

function expectNoAccessibilityViolations(violations: AxeResults["violations"]) {
  expect(
    violations.map((violation) => ({
      id: violation.id,
      targets: violation.nodes.map((node) => node.target.join(" ")),
    })),
  ).toEqual([]);
}

async function seedCourse(
  request: APIRequestContext,
  name: string,
  courseCode: string,
) {
  const response = await request.post("/api/v1/courses", {
    data: {
      name,
      course_code: courseCode,
      description: "Seeded by an independent Courses end-to-end scenario.",
      term: "Autumn 2026",
      color: "#29584c",
    },
  });
  expect(response.ok()).toBeTruthy();
  const course = (await response.json()) as { id: string };
  createdCourseIds.add(course.id);
  return course;
}

async function seedSource(
  request: APIRequestContext,
  courseId: string,
  sourceType: "literature" | "slides",
  fileName: string,
  content: Buffer,
) {
  const query = new URLSearchParams({
    source_type: sourceType,
    file_name: fileName,
  });
  const response = await request.post(
    `/api/v1/courses/${courseId}/sources?${query.toString()}`,
    {
      data: content,
      headers: { "Content-Type": "application/octet-stream" },
    },
  );
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as { id: string };
}

async function openCourse(page: Page, name: string) {
  await page.goto("/");
  await page.getByRole("button", { name: "Courses" }).click();
  await page.getByRole("button", { name: `Open ${name}` }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
}

test("creates, edits, archives, restores, and deletes a course", async ({
  page,
  request,
}) => {
  // This scenario asserts the empty state, so it starts from no courses.
  const existing = await request.get("/api/v1/courses");
  expect(existing.ok()).toBeTruthy();
  for (const course of (await existing.json()) as Array<{ id: string }>) {
    expect(
      (await request.delete(`/api/v1/courses/${course.id}`)).ok(),
    ).toBeTruthy();
  }

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
});

test("links and unlinks a calendar without deleting Calendar data", async ({
  page,
  request,
}) => {
  const calendarResponse = await request.post("/api/v1/calendars", {
    data: {
      name: "Course E2E schedule",
      description: "Calendar linked by the course end-to-end test",
      color: "#8f6ea8",
    },
  });
  expect(calendarResponse.ok()).toBeTruthy();
  const calendar = (await calendarResponse.json()) as { id: string };
  createdCalendarIds.add(calendar.id);
  const eventStart = new Date();
  eventStart.setHours(13, 0, 0, 0);
  const eventEnd = new Date(eventStart.getTime() + 60 * 60 * 1000);
  const eventResponse = await request.post("/api/v1/events", {
    data: {
      calendar_id: calendar.id,
      title: "Course-linked E2E lecture",
      description: null,
      location: "Campus",
      start_at: eventStart.toISOString(),
      end_at: eventEnd.toISOString(),
      all_day: false,
      timezone: "Europe/Oslo",
      recurrence_rule: null,
      status: "confirmed",
    },
  });
  expect(eventResponse.ok()).toBeTruthy();
  const event = (await eventResponse.json()) as { id: string };
  await seedCourse(request, "Calendar linking course", "LINK101");

  await openCourse(page, "Calendar linking course");
  await page.getByRole("tab", { name: "Calendar" }).click();
  await expect(
    page.getByRole("heading", { name: "No calendars linked yet" }),
  ).toBeVisible();
  const sidebar = page.getByRole("complementary", {
    name: "Course calendars",
  });
  await sidebar.getByLabel("Calendar to link").selectOption(calendar.id);
  await sidebar.getByRole("button", { name: "Link calendar" }).click();
  await expect(page.getByText("Course-linked E2E lecture")).toBeVisible();

  await page.getByText("Course-linked E2E lecture").click();
  const eventDialog = page.getByRole("dialog");
  await expect(eventDialog.getByLabel("Title")).toBeEnabled();
  await eventDialog.getByRole("button", { name: "Close", exact: true }).click();

  expectNoAccessibilityViolations(
    (await new AxeBuilder({ page }).analyze()).violations,
  );

  await sidebar
    .getByRole("button", { name: "Unlink Course E2E schedule" })
    .click();
  await expect(
    page.getByRole("heading", { name: "No calendars linked yet" }),
  ).toBeVisible();
  expect((await request.get(`/api/v1/events/${event.id}`)).ok()).toBeTruthy();

  await sidebar.getByLabel("Calendar to link").selectOption(calendar.id);
  await sidebar.getByRole("button", { name: "Link calendar" }).click();
  await expect(page.getByText("Course-linked E2E lecture")).toBeVisible();

  // Deleting a course that still has a linked calendar removes only the link.
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
    page.getByRole("button", { name: "Open Calendar linking course" }),
  ).toHaveCount(0);
  expect(
    (await request.get(`/api/v1/calendars/${calendar.id}`)).ok(),
  ).toBeTruthy();
  expect((await request.get(`/api/v1/events/${event.id}`)).ok()).toBeTruthy();
});

test("uploads Literature and Slides separately and deletes one file", async ({
  page,
  request,
}) => {
  await seedCourse(request, "Materials E2E course", "MAT101");

  await openCourse(page, "Materials E2E course");
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
});

test("opens private Literature and Slides PDFs with byte-range support", async ({
  page,
  request,
}) => {
  const pdf = multiPagePdfFixture();
  expect(pdf.length).toBeGreaterThan(100 * 1024);
  const course = await seedCourse(request, "M15 PDF viewing course", "PDF15");
  const literature = await seedSource(
    request,
    course.id,
    "literature",
    "m15-reading.pdf",
    pdf,
  );
  const slides = await seedSource(
    request,
    course.id,
    "slides",
    "m15-slides.pdf",
    pdf,
  );
  const literatureUrl = `/api/v1/course-sources/${literature.id}/content`;

  const head = await request.head(literatureUrl);
  expect(head.status()).toBe(200);
  expect(head.headers()["content-type"]).toBe("application/pdf");
  expect(head.headers()["content-length"]).toBe(String(pdf.length));
  expect(head.headers()["accept-ranges"]).toBe("bytes");
  const partial = await request.get(literatureUrl, {
    headers: { Range: "bytes=65536-65663" },
  });
  expect(partial.status()).toBe(206);
  expect(partial.headers()["content-range"]).toBe(
    `bytes 65536-65663/${pdf.length}`,
  );
  expect(await partial.body()).toEqual(pdf.subarray(65536, 65664));

  await openCourse(page, "M15 PDF viewing course");
  await page.getByRole("tab", { name: "Materials" }).click();

  const literatureCard = page
    .getByRole("article")
    .filter({ hasText: "m15-reading" });
  const openLiterature = literatureCard.getByRole("button", {
    name: "Open m15-reading PDF",
  });
  await openLiterature.focus();
  await openLiterature.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("m15-reading.pdf")).toBeVisible();
  await expect(
    dialog.locator('object[title="PDF viewer for m15-reading"]'),
  ).toBeVisible();

  expectNoAccessibilityViolations(
    (await new AxeBuilder({ page }).analyze()).violations,
  );

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    dialog.getByRole("link", { name: "Open in new window" }).first(),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);

  await dialog.getByRole("button", { name: "Close PDF viewer" }).click();
  await expect(openLiterature).toBeFocused();

  const slidesCard = page
    .getByRole("article")
    .filter({ hasText: "m15-slides" });
  const newWindowLink = slidesCard.getByRole("link", {
    name: "Open m15-slides PDF in new window",
  });
  await expect(newWindowLink).toHaveAttribute("target", "_blank");
  await expect(newWindowLink).toHaveAttribute(
    "rel",
    /^(?=.*noopener)(?=.*noreferrer)/,
  );
  const [popup, popupRequest] = await Promise.all([
    page.waitForEvent("popup"),
    page.context().waitForEvent("request", {
      predicate: (candidate) =>
        candidate.url().includes(`/api/v1/course-sources/${slides.id}/content`),
    }),
    newWindowLink.click(),
  ]);
  expect(popupRequest.url()).toContain(
    `/api/v1/course-sources/${slides.id}/content`,
  );
  if (!popup.isClosed()) {
    expect(await popup.evaluate(() => window.opener === null)).toBe(true);
    await popup.close();
  }
});

test("writes a Markdown note with a slide reference and restores its disclosure state", async ({
  page,
  request,
}) => {
  const course = await seedCourse(request, "Notes E2E course", "NOTE101");
  await seedSource(
    request,
    course.id,
    "slides",
    "lecture-assets.zip",
    Buffer.from("stored unsupported source"),
  );

  await openCourse(page, "Notes E2E course");
  await page.getByRole("tab", { name: "Notes" }).click();
  await page.getByRole("button", { name: "Create note" }).first().click();
  const noteDialog = page.getByRole("dialog");
  await noteDialog.getByLabel("Note title").fill("Transaction isolation");
  const noteBody = noteDialog.getByLabel("Note body");
  const plainNote = "# Serializable\nAvoid write skew and dirty reads.";
  await noteBody.fill(plainNote);
  await noteBody.evaluate((element: HTMLTextAreaElement) => {
    const start = element.value.indexOf("write skew");
    element.focus();
    element.setSelectionRange(start, start + "write skew".length);
  });
  await noteDialog
    .getByRole("button", { name: "Bold (Ctrl or Command+B)" })
    .click();
  await expect(noteBody).toHaveValue(
    "# Serializable\nAvoid **write skew** and dirty reads.",
  );
  await noteBody.press("Control+z");
  await expect(noteBody).toHaveValue(plainNote);
  await noteBody.evaluate((element: HTMLTextAreaElement) => {
    const start = element.value.indexOf("write skew");
    element.focus();
    element.setSelectionRange(start, start + "write skew".length);
  });
  await noteBody.press("Control+b");
  await noteBody.evaluate((element: HTMLTextAreaElement) => {
    const start = element.value.indexOf("dirty reads");
    element.focus();
    element.setSelectionRange(start, start + "dirty reads".length);
  });
  await noteBody.press("Control+i");
  const markdownNote =
    "# Serializable\nAvoid **write skew** and _dirty reads_.";
  await expect(noteBody).toHaveValue(markdownNote);

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
  await expect(
    note.getByRole("button", { name: "Expand note Transaction isolation" }),
  ).toHaveAttribute("aria-expanded", "false");
  await expect(
    note.getByRole("heading", { level: 4, name: "Serializable" }),
  ).toBeHidden();
  await note
    .getByRole("button", { name: "Expand note Transaction isolation" })
    .click();
  await expect(
    note.getByRole("heading", { level: 4, name: "Serializable" }),
  ).toBeVisible();
  await expect(note.getByText("write skew")).toHaveCSS("font-weight", "700");
  await expect(note.getByText("dirty reads")).toHaveCSS("font-style", "italic");
  await expect(note.getByText("lecture-assets")).toBeVisible();
  await expect(note.getByText("Slides 3–5")).toBeVisible();
  await expect(note.getByText(/Isolation overview/)).toBeVisible();

  // An expanded note collapses again after leaving the tab and after a reload,
  // while the selected course and tab are restored.
  await page.getByRole("tab", { name: "Materials" }).click();
  await page.getByRole("tab", { name: "Notes" }).click();
  await expect(
    note.getByRole("button", { name: "Expand note Transaction isolation" }),
  ).toHaveAttribute("aria-expanded", "false");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Notes E2E course" }),
  ).toBeVisible();
  await expect(page.getByRole("tab", { name: "Notes" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  const reloadedNote = page
    .getByRole("article")
    .filter({ hasText: "Transaction isolation" });
  await expect(
    reloadedNote.getByRole("button", {
      name: "Expand note Transaction isolation",
    }),
  ).toHaveAttribute("aria-expanded", "false");
  await reloadedNote
    .getByRole("button", { name: "Expand note Transaction isolation" })
    .click();

  await reloadedNote.getByRole("button", { name: "Edit" }).click();
  await expect(noteDialog.getByLabel("Note body")).toHaveValue(markdownNote);
  await noteDialog.getByLabel("Note title").fill("Serializable isolation");
  await noteDialog.getByRole("button", { name: "Save changes" }).click();
  await expect(
    page.getByRole("heading", { name: "Serializable isolation" }),
  ).toBeVisible();

  expectNoAccessibilityViolations(
    (await new AxeBuilder({ page }).analyze()).violations,
  );

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
});

test("reviews a prettify suggestion and saves only the accepted version", async ({
  page,
  request,
}) => {
  const prettifyRequests: Array<{ body: string; model: string }> = [];
  await page.route("**/api/v1/notes/prettify", async (route) => {
    const payload = route.request().postDataJSON() as {
      body: string;
      model: string;
    };
    prettifyRequests.push(payload);
    await route.fulfill({
      json: {
        proposed_body: payload.body.replace("Serializble", "Serializable"),
        has_changes: payload.body.includes("Serializble"),
        message: "Review every proposed change before using this draft.",
        model: payload.model,
      },
    });
  });
  await seedCourse(request, "Prettify E2E course", "PRET101");

  await openCourse(page, "Prettify E2E course");
  await page.getByRole("tab", { name: "Notes" }).click();
  await page.getByRole("button", { name: "Create note" }).first().click();
  const noteDialog = page.getByRole("dialog");
  await noteDialog.getByLabel("Note title").fill("Transaction isolation");
  const markdownNote =
    "# Serializable\nAvoid **write skew** and _dirty reads_.";
  const misspelledMarkdown = markdownNote.replace(
    "Serializable",
    "Serializble",
  );
  await noteDialog.getByLabel("Note body").fill(misspelledMarkdown);
  await noteDialog
    .getByLabel("Prettify model")
    .selectOption({ value: "gpt-5.6-terra" });
  await noteDialog.getByRole("button", { name: "Prettify" }).click();
  const comparison = noteDialog.getByRole("region", {
    name: "Prettify comparison",
  });
  await expect(comparison.locator("pre").nth(0)).toHaveText(misspelledMarkdown);
  await expect(comparison.locator("pre").nth(1)).toHaveText(markdownNote);
  expectNoAccessibilityViolations(
    (await new AxeBuilder({ page }).include(".note-prettify-preview").analyze())
      .violations,
  );
  await comparison.getByRole("button", { name: "Keep my version" }).click();
  await expect(noteDialog.getByLabel("Note body")).toHaveValue(
    misspelledMarkdown,
  );
  await noteDialog.getByRole("button", { name: "Prettify" }).click();
  await comparison
    .getByRole("button", { name: "Use prettified version" })
    .click();
  await expect(noteDialog.getByLabel("Note body")).toHaveValue(markdownNote);
  expect(prettifyRequests).toEqual([
    { body: misspelledMarkdown, model: "gpt-5.6-terra" },
    { body: misspelledMarkdown, model: "gpt-5.6-terra" },
  ]);

  await noteDialog.getByRole("button", { name: "Create note" }).click();
  const note = page
    .getByRole("article")
    .filter({ hasText: "Transaction isolation" });
  await note
    .getByRole("button", { name: "Expand note Transaction isolation" })
    .click();
  await expect(
    note.getByRole("heading", { level: 4, name: "Serializable" }),
  ).toBeVisible();
});

test("generates, edits, and regenerates a note summary", async ({
  page,
  request,
}) => {
  let summaryGeneration = 0;
  let storedSummary: Record<string, unknown> | null = null;
  await page.route("**/api/v1/notes/*/summary", async (route) => {
    await route.fulfill({ json: storedSummary });
  });
  await page.route("**/api/v1/notes/*/summaries", async (route) => {
    const noteId = new URL(route.request().url()).pathname.split("/").at(-2)!;
    const payload = route.request().postDataJSON() as { model: string };
    summaryGeneration += 1;
    storedSummary = {
      id: `summary-${noteId}`,
      note_id: noteId,
      model: payload.model,
      status: "completed",
      summary_json: {
        bullets: [
          {
            id: `summary-bullet-${summaryGeneration}`,
            text:
              summaryGeneration === 1
                ? "Isolation helps prevent unsafe transaction interleavings."
                : "A regenerated summary can revisit the source note.",
            origin: "note",
            source_references: [
              { note_id: noteId, source_id: null, slide: null },
            ],
          },
        ],
      },
      note_content_hash: "a".repeat(64),
      slide_content_hash: "b".repeat(64),
      is_stale: false,
      safe_error: null,
      safe_error_code: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    await route.fulfill({ json: storedSummary, status: 201 });
  });
  await page.route("**/api/v1/note-summaries/*/bullets/*", async (route) => {
    storedSummary = {
      ...storedSummary,
      summary_json: { bullets: [] },
      updated_at: new Date().toISOString(),
    };
    await route.fulfill({ json: storedSummary });
  });

  const course = await seedCourse(request, "Summary E2E course", "SUM101");
  const noteResponse = await request.post(
    `/api/v1/courses/${course.id}/notes`,
    {
      data: {
        title: "Transaction isolation",
        body: "# Serializable\nAvoid **write skew** and _dirty reads_.",
        slide_references: [],
      },
    },
  );
  expect(noteResponse.ok()).toBeTruthy();

  await openCourse(page, "Summary E2E course");
  await page.getByRole("tab", { name: "Notes" }).click();
  const note = page
    .getByRole("article")
    .filter({ hasText: "Transaction isolation" });
  await note
    .getByRole("button", { name: "Expand note Transaction isolation" })
    .click();

  await page
    .getByLabel("Summary model")
    .selectOption({ value: "gpt-5.6-terra" });
  await note.getByRole("button", { name: "Generate summary" }).click();
  await expect(
    note.getByRole("button", {
      name: "Expand summary for Transaction isolation",
    }),
  ).toHaveAttribute("aria-expanded", "false");
  await expect(note.getByText("gpt-5.6-terra")).toBeVisible();
  await note
    .getByRole("button", {
      name: "Expand summary for Transaction isolation",
    })
    .click();
  await expect(
    note.getByText(/Isolation helps prevent unsafe transaction interleavings/),
  ).toBeVisible();
  await note.getByRole("button", { name: "Remove summary bullet 1" }).click();
  await expect(note.getByText("No summary bullets remain.")).toBeVisible();
  await expect(note.getByText("Serializable")).toBeVisible();

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Summary E2E course" }),
  ).toBeVisible();
  const reloadedNote = page
    .getByRole("article")
    .filter({ hasText: "Transaction isolation" });
  await reloadedNote
    .getByRole("button", { name: "Expand note Transaction isolation" })
    .click();
  await expect(
    reloadedNote.getByText(/Summary empty · gpt-5.6-terra/),
  ).toBeVisible();
  await reloadedNote.getByRole("button", { name: "Generate again" }).click();
  await reloadedNote
    .getByRole("button", {
      name: "Expand summary for Transaction isolation",
    })
    .click();
  await expect(
    reloadedNote.getByText(
      "A regenerated summary can revisit the source note.",
    ),
  ).toBeVisible();
});
