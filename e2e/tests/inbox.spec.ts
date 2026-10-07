import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { AxeResults } from "axe-core";

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
