import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { AxeResults } from "axe-core";

import { multiPagePdfFixture } from "./pdf-fixture.js";

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    window.localStorage.removeItem("teacher-assistant.ui-state.v1");
  });
});

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

test("creates, tags, downloads, finds, and deletes a private document project", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Documents" }).click();
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
  await page.getByRole("button", { name: "New project" }).click();
  const projectDialog = page.getByRole("dialog");
  await projectDialog.getByLabel("Project title").fill("E2E teaching document");
  await projectDialog.getByRole("button", { name: "Create project" }).click();
  await expect(
    page.getByRole("heading", { name: "E2E teaching document" }),
  ).toBeVisible();

  await page.getByLabel("Tag name").fill("E2E research");
  await page.getByRole("button", { name: "Add tag" }).click();
  await page.getByRole("checkbox", { name: /E2E research/ }).click();
  await expect(
    page.getByRole("checkbox", { name: /E2E research/ }),
  ).toBeChecked();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: /Download main.tex/ }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("main.tex");

  await page.getByLabel("Search projects").fill("no such document");
  await expect(page.getByText("No projects match these filters")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.getByText("E2E teaching document").first()).toBeVisible();

  expectNoAccessibilityViolations(
    (await new AxeBuilder({ page }).include(".documents-page").analyze())
      .violations,
  );

  await page.getByRole("button", { name: "Delete", exact: true }).click();
  const deletion = page.getByRole("alertdialog", {
    name: "Delete E2E teaching document?",
  });
  await expect(deletion).toContainText("private source files");
  await deletion
    .getByRole("button", { name: "Delete project", exact: true })
    .click();
  await expect(page.getByText("Start your first document")).toBeVisible();
});

test("restores Calendar navigation and an unsent Assistant draft", async ({
  page,
}) => {
  const conversation = {
    id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    title: "Persistent E2E conversation",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  await page.route("**/api/v1/assistant/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
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
    await route.abort();
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Day", exact: true }).click();
  await page.getByRole("button", { name: "Previous date range" }).click();
  const rememberedHeading =
    (await page.locator("#calendar-page-title").textContent()) ?? "";

  await page.getByRole("button", { name: "Assistant" }).click();
  const composer = page.getByLabel("Message the Assistant");
  await expect(composer).toBeEnabled();
  await composer.fill("  exact unsent E2E draft  ");

  await page.getByRole("button", { name: "Calendar" }).click();
  await expect(
    page.getByRole("button", { name: "Day", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#calendar-page-title")).toHaveText(
    rememberedHeading,
  );

  await page.getByRole("button", { name: "Assistant" }).click();
  await expect(composer).toHaveValue("  exact unsent E2E draft  ");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Assistant" })).toBeVisible();
  await expect(page.getByLabel("Message the Assistant")).toHaveValue(
    "  exact unsent E2E draft  ",
  );

  expectNoAccessibilityViolations(
    (await new AxeBuilder({ page }).include(".assistant-composer").analyze())
      .violations,
  );
  await page.getByRole("button", { name: "Clear draft" }).click();
  await expect(page.getByLabel("Message the Assistant")).toHaveValue("");
});

test("creates and manages a manual course through the UI", async ({
  page,
  request,
}) => {
  let summaryGeneration = 0;
  let storedSummary: Record<string, unknown> | null = null;
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
  const misspelledMarkdown = markdownNote.replace(
    "Serializable",
    "Serializble",
  );
  await noteBody.fill(misspelledMarkdown);
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

  await page.getByRole("tab", { name: "Materials" }).click();
  await page.getByRole("tab", { name: "Notes" }).click();
  await expect(
    note.getByRole("button", { name: "Expand note Transaction isolation" }),
  ).toHaveAttribute("aria-expanded", "false");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Edited end-to-end databases" }),
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

  await reloadedNote.getByRole("button", { name: "Edit" }).click();
  await expect(noteDialog.getByLabel("Note body")).toHaveValue(markdownNote);
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

test("opens private Literature and Slides PDFs with byte-range support", async ({
  page,
  request,
}) => {
  const pdf = multiPagePdfFixture();
  expect(pdf.length).toBeGreaterThan(100 * 1024);
  const courseResponse = await request.post("/api/v1/courses", {
    data: {
      name: "M15 PDF viewing course",
      course_code: "PDF15",
      description: "Non-private end-to-end PDF viewing fixture.",
      term: "Autumn 2026",
      color: "#29584c",
    },
  });
  expect(courseResponse.ok()).toBeTruthy();
  const course = (await courseResponse.json()) as { id: string };

  async function uploadPdf(
    sourceType: "literature" | "slides",
    fileName: string,
  ) {
    const query = new URLSearchParams({
      source_type: sourceType,
      file_name: fileName,
    });
    const response = await request.post(
      `/api/v1/courses/${course.id}/sources?${query.toString()}`,
      {
        data: pdf,
        headers: { "Content-Type": "application/octet-stream" },
      },
    );
    expect(response.ok()).toBeTruthy();
    return (await response.json()) as { id: string };
  }

  const literature = await uploadPdf("literature", "m15-reading.pdf");
  const slides = await uploadPdf("slides", "m15-slides.pdf");
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

  await page.goto("/");
  await page.getByRole("button", { name: "Courses" }).click();
  await page
    .getByRole("button", { name: "Open M15 PDF viewing course" })
    .click();
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

  const accessibility = await new AxeBuilder({ page }).analyze();
  expectNoAccessibilityViolations(accessibility.violations);

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
      predicate: (request) =>
        request.url().includes(`/api/v1/course-sources/${slides.id}/content`),
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

test("shows actionable Assistant failure details without exposing raw model output", async ({
  page,
}) => {
  const timestamp = new Date().toISOString();
  const conversation = {
    id: "e2e-failed-conversation",
    title: "Why was my reply blocked?",
    created_at: timestamp,
    updated_at: timestamp,
  };
  const failedJob = {
    id: "e2e-failed-job",
    conversation_id: conversation.id,
    owner_message_id: "e2e-owner-message",
    status: "failed",
    model: "gpt-5.6-sol",
    safe_error:
      "The assistant's reply did not match the required safe response format, so the backend rejected it before saving an answer or changing calendar data.",
    safe_error_code: "invalid_assistant_response",
    safe_error_details: {
      failure_stage: "validating",
      validation_stage: "response_schema",
      reason:
        "The response JSON did not match the required assistant answer schema.",
      automatic_retry_attempted: true,
      validation_errors: [
        {
          field: "proposal.actions.0.operation",
          message: "The action is not supported.",
          type: "union_tag_invalid",
        },
      ],
      owner_actions: [
        "The Assistant already corrected its response once automatically. Review the reason below, then retry manually or rephrase the request.",
      ],
      developer_actions: [
        "Inspect the validation stage and field issues below. Raw model output is intentionally not logged or exposed.",
      ],
    },
    diagnostic_error_id: "e2e-diagnostic-report",
    created_at: timestamp,
    updated_at: timestamp,
  };

  await page.route("**/api/v1/assistant/auth", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        authenticated: true,
        auth_type: "chatgpt",
        email: "owner@example.test",
        plan_type: "plus",
      }),
    });
  });
  await page.route("**/api/v1/assistant/conversations", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([conversation]),
    });
  });
  await page.route(
    `**/api/v1/assistant/conversations/${conversation.id}`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...conversation,
          messages: [
            {
              id: "e2e-owner-message",
              conversation_id: conversation.id,
              role: "owner",
              content: "Can you help with this?",
              citations: [],
              job_id: null,
              created_at: timestamp,
            },
          ],
          jobs: [failedJob],
          proposals: [],
        }),
      });
    },
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Assistant" }).click();
  await page
    .getByRole("button", { name: /Why was my reply blocked\?/ })
    .click();

  await expect(
    page.getByText("The reply was blocked for safety"),
  ).toBeVisible();
  await expect(
    page.getByText(
      "The response JSON did not match the required assistant answer schema.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Ask Assistant about this error" }),
  ).toBeVisible();
  await page.getByText("Developer details").click();
  await expect(page.getByText("response_schema")).toBeVisible();
  await expect(page.getByText(/proposal\.actions\.0\.operation/)).toBeVisible();
  await expect(page.getByText("raw private model response")).toHaveCount(0);

  const accessibility = await new AxeBuilder({ page })
    .include(".assistant-job-error")
    .analyze();
  expectNoAccessibilityViolations(accessibility.violations);
});

test("shows thinking progress and cancels a long Assistant request", async ({
  page,
}) => {
  const timestamp = new Date().toISOString();
  const conversation = {
    id: "e2e-cancel-conversation",
    title: "Long Assistant request",
    created_at: timestamp,
    updated_at: timestamp,
  };
  const ownerMessage = {
    id: "e2e-cancel-owner-message",
    conversation_id: conversation.id,
    role: "owner",
    content: "Explain tomorrow in detail.",
    citations: [],
    job_id: null,
    created_at: timestamp,
  };
  const cancelledJob = {
    id: "e2e-cancel-job",
    conversation_id: conversation.id,
    owner_message_id: ownerMessage.id,
    status: "cancelled",
    model: "gpt-5.6-sol",
    safe_error:
      "You cancelled this request. No Assistant answer or calendar change was saved.",
    safe_error_code: "assistant_job_cancelled",
    safe_error_details: {},
    diagnostic_error_id: null,
    created_at: timestamp,
    updated_at: timestamp,
  };
  let messageStarted = false;
  let cancelled = false;
  let releaseMessage: (() => void) | undefined;

  await page.route("**/api/v1/assistant/auth", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        authenticated: true,
        auth_type: "chatgpt",
        email: "owner@example.test",
        plan_type: "plus",
      }),
    });
  });
  await page.route("**/api/v1/assistant/conversations", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([conversation]),
    });
  });
  await page.route(
    `**/api/v1/assistant/conversations/${conversation.id}`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...conversation,
          messages: cancelled ? [ownerMessage] : [],
          jobs: cancelled ? [cancelledJob] : [],
          proposals: [],
        }),
      });
    },
  );
  await page.route(
    `**/api/v1/assistant/conversations/${conversation.id}/messages`,
    async (route) => {
      messageStarted = true;
      await new Promise<void>((resolve) => {
        releaseMessage = resolve;
      });
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          conversation,
          owner_message: ownerMessage,
          assistant_message: null,
          job: cancelledJob,
          proposal: null,
          proposals: [],
        }),
      });
    },
  );
  await page.route(
    `**/api/v1/assistant/conversations/${conversation.id}/cancel`,
    async (route) => {
      cancelled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(cancelledJob),
      });
      setTimeout(() => releaseMessage?.(), 100);
    },
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Assistant" }).click();
  await page.getByLabel("Message the Assistant").fill(ownerMessage.content);
  await page.getByRole("button", { name: "Send message" }).click();
  await expect.poll(() => messageStarted).toBe(true);
  await expect(page.getByText("Thinking through your request…")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Cancel request" }),
  ).toBeVisible();

  const thinkingAccessibility = await new AxeBuilder({ page })
    .include(".assistant-thinking")
    .analyze();
  expectNoAccessibilityViolations(thinkingAccessibility.violations);

  await page.getByRole("button", { name: "Cancel request" }).click();
  await expect(page.getByText("Request cancelled")).toBeVisible();
  await expect(
    page.getByText(/No Assistant answer or calendar change was saved/),
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

test("connects a dedicated mailbox and reads forwarded mail safely", async ({
  page,
}) => {
  const messageId = "11111111-1111-4111-8111-111111111111";
  let connected = false;
  let read = false;
  let archived = false;
  const status = () => ({
    connected,
    status: connected ? "connected" : null,
    host: connected ? "imap.example.com" : null,
    port: connected ? 993 : null,
    tls_mode: connected ? "implicit_tls" : null,
    mailbox: connected ? "INBOX" : null,
    username: connected ? "dedicated@example.com" : null,
    last_checked_at: null,
    last_success_at: null,
    next_check_at: connected ? "2026-09-03T12:00:00Z" : null,
    safe_error_code: null,
    safe_error: null,
    source_warning: null,
    quarantined_count: 0,
  });
  const listItem = () => ({
    id: messageId,
    subject: "Forwarded exam-room update",
    sender_name: "School Office",
    sender_address: "office@example.edu",
    recipients: ["dedicated@example.com"],
    source_date: "2026-09-03T07:00:00Z",
    ingested_at: "2026-09-03T07:01:00Z",
    attachment_count: 1,
    omitted_attachment_count: 0,
    is_read: read,
    is_archived: archived,
    forwarded_unverified: true,
    source_label: "Mail",
  });
  const detail = () => ({
    ...listItem(),
    message_id: "<exam-room@example.edu>",
    in_reply_to: null,
    thread_references: [],
    body_text: "The exam room has changed to A-204.",
    body_html: null,
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
        original_filename: "room-map.pdf",
        mime_type: "application/pdf",
        file_size: 128,
        status: "stored",
        omission_reason: null,
      },
    ],
  });

  await page.route("**/api/v1/integrations/mail**", async (route) => {
    const request = route.request();
    if (request.method() === "PUT") {
      const body = request.postDataJSON() as { password: string };
      expect(body.password).toBe("app-password-fixture");
      connected = true;
    }
    await route.fulfill({ json: status() });
  });
  await page.route("**/api/v1/inbox**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    if (pathname === `/api/v1/inbox/${messageId}`) {
      if (request.method() === "PATCH") {
        const changes = request.postDataJSON() as {
          is_read?: boolean;
          is_archived?: boolean;
        };
        if (changes.is_read !== undefined) read = changes.is_read;
        if (changes.is_archived !== undefined) archived = changes.is_archived;
      }
      await route.fulfill({ json: detail() });
      return;
    }
    const query = new URL(request.url()).searchParams;
    const showArchived = query.get("archived") === "true";
    await route.fulfill({
      json: showArchived === archived ? [listItem()] : [],
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();
  await page.getByLabel("IMAP host").fill("imap.example.com");
  await page.getByLabel("Username").fill("dedicated@example.com");
  await page.getByLabel(/^App password/).fill("app-password-fixture");
  await page.getByRole("button", { name: "Connect mailbox" }).click();
  await expect(page.getByText(/tested and connected/i)).toBeVisible();
  await expect(page.getByLabel(/^App password/)).toHaveValue("");
  await expect(page.getByText("app-password-fixture")).toHaveCount(0);

  expectNoAccessibilityViolations(
    (await new AxeBuilder({ page }).analyze()).violations,
  );

  await page.getByRole("button", { name: "Inbox" }).click();
  await page.getByRole("button", { name: /School Office/i }).click();
  await expect(
    page.getByRole("heading", { name: "Forwarded exam-room update" }),
  ).toBeVisible();
  await expect(page.getByText(/forwarded content unverified/i)).toBeVisible();
  await expect(
    page.getByText("The exam room has changed to A-204."),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Download" })).toHaveAttribute(
    "href",
    "/api/v1/mail-attachments/22222222-2222-4222-8222-222222222222/content",
  );
  expectNoAccessibilityViolations(
    (await new AxeBuilder({ page }).analyze()).violations,
  );
});
