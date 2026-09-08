import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DocumentsPage } from "./DocumentsPage";

const now = "2026-09-08T10:00:00Z";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("DocumentsPage", () => {
  it("creates, opens, tags, renames, and confirms deletion", async () => {
    let projects: Array<Record<string, unknown>> = [];
    let tags: Array<Record<string, unknown>> = [];
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        if (url.includes("/document-projects?") && method === "GET")
          return json(projects);
        if (url.endsWith("/document-tags") && method === "GET")
          return json(tags);
        if (url.endsWith("/document-projects") && method === "POST") {
          const title = JSON.parse(String(init?.body)).title;
          const project = {
            id: "11111111-1111-4111-8111-111111111111",
            title,
            tags: [],
            created_at: now,
            updated_at: now,
          };
          projects = [project];
          return json(project, 201);
        }
        if (url.endsWith("/document-tags") && method === "POST") {
          const payload = JSON.parse(String(init?.body));
          const tag = {
            id: "22222222-2222-4222-8222-222222222222",
            ...payload,
            project_count: 0,
            created_at: now,
            updated_at: now,
          };
          tags = [tag];
          return json(tag, 201);
        }
        if (url.includes("/tags/") && method === "PUT") {
          projects = [
            {
              ...projects[0],
              tags: [
                { id: tags[0].id, name: tags[0].name, color: tags[0].color },
              ],
            },
          ];
          tags = [{ ...tags[0], project_count: 1 }];
          return json(projects[0]);
        }
        if (url.includes("/document-projects/") && method === "PATCH") {
          const title = JSON.parse(String(init?.body)).title;
          projects = [{ ...projects[0], title }];
          return json(projects[0]);
        }
        if (url.includes("/document-projects/") && method === "DELETE") {
          projects = [];
          return new Response(null, { status: 204 });
        }
        throw new Error(`Unexpected request: ${method} ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<DocumentsPage />);
    expect(
      await screen.findByText("Start your first document"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "New project" }));
    fireEvent.change(screen.getByLabelText("Project title"), {
      target: { value: "Lesson notes" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create project" }));
    expect(
      await screen.findByRole("heading", { name: "Lesson notes" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Download main.tex/ }),
    ).toHaveAttribute("href", expect.stringContaining("/main.tex"));

    fireEvent.change(screen.getByLabelText("Tag name"), {
      target: { value: "Teaching" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add tag" }));
    const assignment = await screen.findByRole("checkbox", {
      name: /Teaching/,
    });
    fireEvent.click(assignment);
    await waitFor(() => expect(assignment).toBeChecked());

    fireEvent.click(screen.getByRole("button", { name: "Rename" }));
    fireEvent.change(screen.getByLabelText("Project title"), {
      target: { value: "Updated lesson" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save title" }));
    expect(await screen.findAllByText("Updated lesson")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(
      screen.getByRole("alertdialog", { name: "Delete Updated lesson?" }),
    ).toHaveTextContent("private source files");
    fireEvent.click(screen.getByRole("button", { name: "Delete project" }));
    expect(
      await screen.findByText("Start your first document"),
    ).toBeInTheDocument();
  });

  it("composes search and tag filters and shows a readable empty state", async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const url = String(input);
      if (url.endsWith("/document-tags"))
        return json([
          {
            id: "22222222-2222-4222-8222-222222222222",
            name: "Research",
            color: "#123456",
            project_count: 0,
            created_at: now,
            updated_at: now,
          },
        ]);
      if (url.includes("/document-projects?")) return json([]);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<DocumentsPage />);

    fireEvent.change(screen.getByLabelText("Search projects"), {
      target: { value: "missing" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Research" }));
    expect(
      await screen.findByText("No projects match these filters"),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url]) =>
            String(url).includes("search=missing") &&
            String(url).includes("tag_id=22222222"),
        ),
      ).toBe(true),
    );
  });
});
