import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NoteDialog } from "./NoteDialog";
import type { CourseNote } from "./types";

const original = "# Transactons\n- This are **importent** notes.";
const proposed = "# Transactions\n- These are **important** notes.";
const now = "2026-09-01T12:00:00Z";

const note: CourseNote = {
  id: "note-1",
  course_id: "course-1",
  title: "Draft",
  body: original,
  slide_references: [],
  created_at: now,
  updated_at: now,
};

function jsonResponse(value: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(value), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function installFetch({
  prettifyBody = proposed,
  prettifyStatus = 200,
}: {
  prettifyBody?: string;
  prettifyStatus?: number;
} = {}) {
  return vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/api/v1/ai/models")) {
      return jsonResponse({
        default_model: "gpt-5.6-sol",
        models: [
          { id: "gpt-5.6-sol", label: "GPT-5.6 Sol · flagship" },
          { id: "gpt-5.6-luna", label: "GPT-5.6 Luna · efficient" },
        ],
      });
    }
    if (url.endsWith("/api/v1/notes/prettify") && init?.method === "POST") {
      if (prettifyStatus !== 200) {
        return jsonResponse(
          {
            code: "invalid_note_prettify_response",
            message: "The suggestion was rejected. The note was not changed.",
          },
          prettifyStatus,
        );
      }
      const payload = JSON.parse(String(init.body));
      return jsonResponse({
        proposed_body: prettifyBody,
        has_changes: prettifyBody !== payload.body,
        message:
          prettifyBody === payload.body
            ? "No clear corrections were found."
            : "Review every proposed change before using this draft.",
        model: payload.model,
      });
    }
    throw new Error(`Unhandled request: ${url}`);
  });
}

describe("NoteDialog prettify", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows every change, requires acceptance, and saves only through normal save", async () => {
    const fetchMock = installFetch();
    vi.stubGlobal("fetch", fetchMock);
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <NoteDialog
        note={note}
        onClose={vi.fn()}
        onSave={onSave}
        slideSources={[]}
      />,
    );

    const model = await screen.findByLabelText("Prettify model");
    fireEvent.change(model, { target: { value: "gpt-5.6-luna" } });
    fireEvent.click(screen.getByRole("button", { name: "Prettify" }));

    const comparison = await screen.findByRole("region", {
      name: "Prettify comparison",
    });
    expect(within(comparison).getByText("Your version")).toBeInTheDocument();
    const previews = comparison.querySelectorAll("pre");
    expect(previews[0]).toHaveTextContent("# Transactons");
    expect(previews[0].textContent).toBe(original);
    expect(previews[1].textContent).toBe(proposed);
    expect(onSave).not.toHaveBeenCalled();
    const prettifyCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/api/v1/notes/prettify"),
    );
    expect(JSON.parse(String(prettifyCall?.[1]?.body))).toEqual({
      body: original,
      model: "gpt-5.6-luna",
    });

    fireEvent.click(
      within(comparison).getByRole("button", {
        name: "Use prettified version",
      }),
    );
    const editor = screen.getByLabelText("Note body");
    expect(editor).toHaveValue(proposed);
    await waitFor(() => expect(editor).toHaveFocus());
    expect(screen.getByRole("status")).toHaveTextContent("unsaved draft");
    expect(onSave).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave.mock.calls[0][0].body).toBe(proposed);
  });

  it("keeps the draft byte-for-byte when rejected and when preview is closed", async () => {
    vi.stubGlobal("fetch", installFetch());
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();
    render(
      <NoteDialog
        note={note}
        onClose={onClose}
        onSave={onSave}
        slideSources={[]}
      />,
    );
    await screen.findByLabelText("Prettify model");
    fireEvent.click(screen.getByRole("button", { name: "Prettify" }));
    let comparison = await screen.findByRole("region", {
      name: "Prettify comparison",
    });
    fireEvent.click(
      within(comparison).getByRole("button", { name: "Keep my version" }),
    );
    expect(screen.getByLabelText("Note body")).toHaveValue(original);
    expect(screen.getByRole("status")).toHaveTextContent("original draft");

    fireEvent.click(screen.getByRole("button", { name: "Prettify" }));
    comparison = await screen.findByRole("region", {
      name: "Prettify comparison",
    });
    expect(comparison).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close note dialog" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onSave).not.toHaveBeenCalled();
  });

  it("preserves the editor draft on failure and handles no-change suggestions", async () => {
    vi.stubGlobal("fetch", installFetch({ prettifyStatus: 503 }));
    const view = render(
      <NoteDialog
        note={note}
        onClose={vi.fn()}
        onSave={vi.fn()}
        slideSources={[]}
      />,
    );
    await screen.findByLabelText("Prettify model");
    fireEvent.click(screen.getByRole("button", { name: "Prettify" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The suggestion was rejected",
    );
    expect(screen.getByLabelText("Note body")).toHaveValue(original);

    view.unmount();
    vi.stubGlobal("fetch", installFetch({ prettifyBody: original }));
    render(
      <NoteDialog
        note={note}
        onClose={vi.fn()}
        onSave={vi.fn()}
        slideSources={[]}
      />,
    );
    await screen.findByLabelText("Prettify model");
    fireEvent.click(screen.getByRole("button", { name: "Prettify" }));
    expect(
      await screen.findByText("No clear corrections were found."),
    ).toHaveAttribute("role", "status");
    expect(
      screen.queryByRole("region", { name: "Prettify comparison" }),
    ).toBeNull();
    expect(screen.getByLabelText("Note body")).toHaveValue(original);
  });

  it("cancels an in-flight request without changing the draft", async () => {
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        if (String(input).endsWith("/api/v1/ai/models")) {
          return jsonResponse({
            default_model: "gpt-5.6-sol",
            models: [{ id: "gpt-5.6-sol", label: "GPT-5.6 Sol" }],
          });
        }
        return await new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Cancelled", "AbortError"));
          });
        });
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(
      <NoteDialog
        note={note}
        onClose={vi.fn()}
        onSave={vi.fn()}
        slideSources={[]}
      />,
    );
    await screen.findByLabelText("Prettify model");
    fireEvent.click(screen.getByRole("button", { name: "Prettify" }));
    expect(screen.getByLabelText("Note body")).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Cancel prettify" }));
    expect(
      await screen.findByText("Prettify cancelled. Your draft is unchanged."),
    ).toHaveAttribute("role", "status");
    expect(screen.getByLabelText("Note body")).toHaveValue(original);
    expect(screen.getByLabelText("Note body")).not.toBeDisabled();
  });
});
