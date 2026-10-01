import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { AxeResults } from "axe-core";

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

test("restores Calendar navigation and an unsent Assistant draft", async ({
  page,
  request,
}) => {
  const seed = await request.post("/api/v1/calendars", {
    data: { name: "Persistence E2E", color: "#29584c" },
  });
  expect(seed.ok()).toBeTruthy();
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
    "**/api/v1/diagnostics/errors/e2e-sanitized-error/explain",
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

  // Leave no course behind for scenarios that assert the empty course list.
  expect(
    (await request.delete(`/api/v1/courses/${course.id}`)).ok(),
  ).toBeTruthy();
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
