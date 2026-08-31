import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { MarkdownNoteEditor } from "./MarkdownNoteEditor";

afterEach(cleanup);

function EditorHarness({
  initial,
  maxLength,
}: {
  initial: string;
  maxLength?: number;
}) {
  const [value, setValue] = useState(initial);
  return (
    <MarkdownNoteEditor
      maxLength={maxLength}
      onChange={setValue}
      value={value}
    />
  );
}

describe("MarkdownNoteEditor", () => {
  it("keeps syntax visible while styling its meaning", () => {
    const { container } = render(
      <EditorHarness
        initial={
          "# Heading\n**jere** and _emphasis_ with [link](https://example.com) and `code`\n- item\n> quote\n```ts\nconst safe = true;\n```"
        }
      />,
    );

    expect(screen.getByLabelText("Note body")).toHaveValue(
      "# Heading\n**jere** and _emphasis_ with [link](https://example.com) and `code`\n- item\n> quote\n```ts\nconst safe = true;\n```",
    );
    const overlay = container.querySelector(".markdown-editor-highlight")!;
    expect(overlay).toHaveTextContent("# Heading");
    expect(
      overlay.querySelector(".markdown-source-strong strong"),
    ).toHaveTextContent("jere");
    expect(
      overlay.querySelector(".markdown-source-emphasis em"),
    ).toHaveTextContent("emphasis");
    expect(
      overlay.querySelector(".markdown-source-marker"),
    ).toBeInTheDocument();
    expect(
      overlay.querySelector(".markdown-source-code-block"),
    ).toHaveTextContent("const safe = true;");
  });

  it("formats the current selection with toolbar and keyboard operations", async () => {
    render(<EditorHarness initial="jere" />);
    const textarea = screen.getByLabelText("Note body") as HTMLTextAreaElement;
    textarea.focus();
    textarea.setSelectionRange(0, 4);
    fireEvent.click(screen.getByRole("button", { name: /Bold/ }));

    expect(textarea).toHaveValue("**jere**");
    await waitFor(() => {
      expect(textarea.selectionStart).toBe(2);
      expect(textarea.selectionEnd).toBe(6);
    });

    fireEvent.change(textarea, { target: { value: "italic" } });
    textarea.setSelectionRange(0, 6);
    fireEvent.keyDown(textarea, { ctrlKey: true, key: "i" });
    expect(textarea).toHaveValue("_italic_");

    fireEvent.change(textarea, { target: { value: "first\nsecond" } });
    textarea.setSelectionRange(0, textarea.value.length);
    fireEvent.click(screen.getByRole("button", { name: "Numbered list" }));
    expect(textarea).toHaveValue("1. first\n2. second");
  });

  it("offers every required toolbar action and a plain-text fallback", () => {
    const { container } = render(
      <EditorHarness initial="plain **Markdown**" />,
    );
    const toolbar = screen.getByRole("toolbar", {
      name: "Markdown formatting",
    });
    for (const name of [
      /Bold/,
      /Italic/,
      "Heading",
      "Bulleted list",
      "Numbered list",
      "Blockquote",
      "Link",
      "Inline code",
      "Code block",
    ]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }

    fireEvent.click(
      screen.getByRole("button", { name: "Use plain-text fallback" }),
    );
    expect(toolbar.closest(".markdown-editor")).toHaveClass("plain-text");
    expect(
      container.querySelector(".markdown-editor-highlight"),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Note body")).toHaveValue(
      "plain **Markdown**",
    );
    expect(
      screen.getByText(/Plain-text editing mode.*stored exactly as typed/),
    ).toBeInTheDocument();
  });

  it("shows the character limit and blocks toolbar overflow", () => {
    render(<EditorHarness initial="123456789" maxLength={10} />);
    const textarea = screen.getByLabelText("Note body") as HTMLTextAreaElement;
    expect(screen.getByText("9 / 10 characters")).toBeInTheDocument();

    textarea.setSelectionRange(9, 9);
    fireEvent.click(screen.getByRole("button", { name: /Bold/ }));
    expect(textarea).toHaveValue("123456789");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "exceed the 10-character note limit",
    );
  });
});
