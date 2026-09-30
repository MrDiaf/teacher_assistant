import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    window.localStorage.removeItem("teacher-assistant.ui-state.v1");
  });
});

async function openDocuments(page: Page) {
  await page.getByRole("button", { name: "Documents" }).click();
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
}

test("uses the real API and private storage for the Documents workflow", async ({
  page,
}) => {
  await openDocuments(page);
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

  const accessibility = await new AxeBuilder({ page })
    .include(".documents-page")
    .analyze();
  expect(
    accessibility.violations.map((violation) => ({
      id: violation.id,
      targets: violation.nodes.map((node) => node.target.join(" ")),
    })),
  ).toEqual([]);

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

test("supports a reversible contract-checked fixture-only UI exercise", async ({
  page,
}) => {
  const project = {
    id: "33333333-3333-4333-8333-333333333333",
    title: "Fixture document",
    tags: [],
    created_at: "2026-09-08T10:00:00Z",
    updated_at: "2026-09-08T10:00:00Z",
  };
  const seen: string[] = [];

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (!url.pathname.startsWith("/api/v1/document-")) {
      await route.fallback();
      return;
    }
    seen.push(`${request.method()} ${url.pathname}`);
    if (
      request.method() === "GET" &&
      url.pathname === "/api/v1/document-projects"
    ) {
      await route.fulfill({ json: [project] });
      return;
    }
    if (
      request.method() === "GET" &&
      url.pathname === "/api/v1/document-tags"
    ) {
      await route.fulfill({ json: [] });
      return;
    }
    if (
      request.method() === "PATCH" &&
      url.pathname === `/api/v1/document-projects/${project.id}`
    ) {
      const payload = request.postDataJSON() as Record<string, unknown>;
      expect(Object.keys(payload)).toEqual(["title"]);
      expect(typeof payload.title).toBe("string");
      project.title = String(payload.title);
      await route.fulfill({ json: project });
      return;
    }
    throw new Error(
      `Fixture rejected undeclared Documents request: ${request.method()} ${url.pathname}`,
    );
  });

  await page.reload();
  await openDocuments(page);
  await page.getByRole("button", { name: "Open", exact: true }).click();
  await page.getByRole("button", { name: "Rename", exact: true }).click();
  await page.getByLabel("Project title").fill("Fixture renamed locally");
  await page.getByRole("button", { name: "Save title" }).click();
  await expect(page.getByText("Fixture renamed locally").first()).toBeVisible();
  expect(seen).toContain(`PATCH /api/v1/document-projects/${project.id}`);
});
