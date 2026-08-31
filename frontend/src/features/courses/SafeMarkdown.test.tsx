import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SafeMarkdown } from "./SafeMarkdown";

afterEach(cleanup);

describe("SafeMarkdown", () => {
  it("renders the supported Markdown subset with semantic elements", () => {
    const { container } = render(
      <SafeMarkdown
        source={
          "# Heading\n\nA **bold** and _careful_ [link](https://example.com) with `inline`.\n\n- first\n- second\n\n3. third\n4. fourth\n\n> quoted text\n\n```ts\nconst answer = 42;\n```"
        }
      />,
    );

    expect(
      screen.getByRole("heading", { level: 4, name: "Heading" }),
    ).toBeInTheDocument();
    expect(screen.getByText("bold").tagName).toBe("STRONG");
    expect(screen.getByText("careful").tagName).toBe("EM");
    expect(screen.getByRole("link", { name: "link" })).toHaveAttribute(
      "href",
      "https://example.com",
    );
    expect(screen.getByText("inline").tagName).toBe("CODE");
    expect(
      within(screen.getAllByRole("list")[0]).getByText("first"),
    ).toBeInTheDocument();
    expect(container.querySelector("ol")).toHaveAttribute("start", "3");
    expect(container.querySelector("blockquote")).toHaveTextContent(
      "quoted text",
    );
    expect(container.querySelector("pre code")).toHaveTextContent(
      "const answer = 42;",
    );
  });

  it("never creates active content and removes unsafe link targets", () => {
    const source = [
      "<script>window.hacked = true</script>",
      '<iframe src="https://example.com"></iframe>',
      '<img src=x onerror="window.hacked = true">',
      "[bad](javascript:alert(1))",
      "[data](data:text/html,boom)",
      "[safe](mailto:owner@example.test)",
    ].join("\n\n");
    const { container } = render(<SafeMarkdown source={source} />);

    expect(container.querySelector("script, iframe, img")).toBeNull();
    expect(container).toHaveTextContent(
      "<script>window.hacked = true</script>",
    );
    expect(container).toHaveTextContent(
      '<iframe src="https://example.com"></iframe>',
    );
    expect(
      screen.getByLabelText("bad (unsafe link removed)"),
    ).not.toHaveAttribute("href");
    expect(
      screen.getByLabelText("data (unsafe link removed)"),
    ).not.toHaveAttribute("href");
    expect(screen.getByRole("link", { name: "safe" })).toHaveAttribute(
      "href",
      "mailto:owner@example.test",
    );
    expect((window as Window & { hacked?: boolean }).hacked).not.toBe(true);
  });

  it("keeps malformed Markdown and plain text readable", () => {
    const { container, rerender } = render(
      <SafeMarkdown
        source={"**unclosed emphasis\n[broken](\n```\nreadable code"}
      />,
    );
    expect(container).toHaveTextContent("**unclosed emphasis");
    expect(container).toHaveTextContent("[broken](");
    expect(container).toHaveTextContent("readable code");

    rerender(<SafeMarkdown source="A normal note with no Markdown." />);
    expect(screen.getByText("A normal note with no Markdown.").tagName).toBe(
      "P",
    );
  });
});
