import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DocumentsPage } from "./DocumentsPage";
import { createFakeDocumentsProvider } from "./testing/fakeDocumentsProvider";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("DocumentsPage", () => {
  it("creates, opens, tags, renames, and confirms deletion", async () => {
    const provider = createFakeDocumentsProvider();
    const fetchMock = vi.fn(provider.fetch);
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
    const provider = createFakeDocumentsProvider({
      tags: [
        {
          id: "22222222-2222-4222-8222-222222222222",
          name: "Research",
          color: "#123456",
          project_count: 0,
          created_at: "2026-09-08T10:00:00Z",
          updated_at: "2026-09-08T10:00:00Z",
        },
      ],
    });
    const fetchMock = vi.fn(provider.fetch);
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
