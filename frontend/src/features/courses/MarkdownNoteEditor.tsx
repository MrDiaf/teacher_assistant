import {
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

const DEFAULT_MAX_LENGTH = 100_000;
const INLINE_MARKDOWN =
  /(`([^`\n]+)`)|(\[([^\]\n]+)\]\(([^)\n]*)\))|(\*\*([^*\n]+)\*\*)|(__([^_\n]+)__)|(\*([^*\n]+)\*)|(_([^_\n]+)_)/g;

function highlightedInline(source: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let token = 0;

  for (const match of source.matchAll(INLINE_MARKDOWN)) {
    const index = match.index ?? 0;
    if (index > cursor) nodes.push(source.slice(cursor, index));
    const key = `${keyPrefix}-${token}`;
    token += 1;

    if (match[1]) {
      nodes.push(
        <span className="markdown-source-inline-code" key={key}>
          <span className="markdown-source-marker">`</span>
          <span>{match[2]}</span>
          <span className="markdown-source-marker">`</span>
        </span>,
      );
    } else if (match[3]) {
      nodes.push(
        <span className="markdown-source-link" key={key}>
          <span className="markdown-source-marker">[</span>
          <span className="markdown-source-link-text">{match[4]}</span>
          <span className="markdown-source-marker">](</span>
          <span className="markdown-source-url">{match[5]}</span>
          <span className="markdown-source-marker">)</span>
        </span>,
      );
    } else if (match[6] || match[8]) {
      const marker = match[6] ? "**" : "__";
      nodes.push(
        <span className="markdown-source-strong" key={key}>
          <span className="markdown-source-marker">{marker}</span>
          <strong>{match[7] ?? match[9]}</strong>
          <span className="markdown-source-marker">{marker}</span>
        </span>,
      );
    } else {
      const marker = match[10] ? "*" : "_";
      nodes.push(
        <span className="markdown-source-emphasis" key={key}>
          <span className="markdown-source-marker">{marker}</span>
          <em>{match[11] ?? match[13]}</em>
          <span className="markdown-source-marker">{marker}</span>
        </span>,
      );
    }
    cursor = index + match[0].length;
  }

  if (cursor < source.length) nodes.push(source.slice(cursor));
  return nodes;
}

export function highlightMarkdownSource(source: string): ReactNode[] {
  const lines = source.split("\n");
  const nodes: ReactNode[] = [];
  let inFence = false;

  lines.forEach((line, index) => {
    const fence = line.match(/^(\s*)(```.*)$/);
    let content: ReactNode;
    let className = "markdown-source-line";

    if (fence) {
      className += " markdown-source-fence";
      content = (
        <>
          {fence[1]}
          <span className="markdown-source-marker">{fence[2]}</span>
        </>
      );
      inFence = !inFence;
    } else if (inFence) {
      className += " markdown-source-code-block";
      content = line;
    } else {
      const heading = line.match(/^(\s{0,3})(#{1,6})(\s+)(.*)$/);
      const quote = line.match(/^(\s*)(>)(\s?)(.*)$/);
      const unordered = line.match(/^(\s*)([-+*])(\s+)(.*)$/);
      const ordered = line.match(/^(\s*)(\d+[.)])(\s+)(.*)$/);

      if (heading) {
        className += " markdown-source-heading";
        content = (
          <>
            {heading[1]}
            <span className="markdown-source-marker">{heading[2]}</span>
            {heading[3]}
            <span className="markdown-source-heading-text">
              {highlightedInline(heading[4], `heading-${index}`)}
            </span>
          </>
        );
      } else if (quote) {
        className += " markdown-source-quote";
        content = (
          <>
            {quote[1]}
            <span className="markdown-source-marker">{quote[2]}</span>
            {quote[3]}
            {highlightedInline(quote[4], `quote-${index}`)}
          </>
        );
      } else if (unordered || ordered) {
        const list = unordered ?? ordered!;
        className += ordered
          ? " markdown-source-ordered-list"
          : " markdown-source-unordered-list";
        content = (
          <>
            {list[1]}
            <span className="markdown-source-marker">{list[2]}</span>
            {list[3]}
            {highlightedInline(list[4], `list-${index}`)}
          </>
        );
      } else {
        content = highlightedInline(line, `line-${index}`);
      }
    }

    nodes.push(
      <span className={className} key={`line-${index}`}>
        {content}
      </span>,
    );
    if (index < lines.length - 1) nodes.push("\n");
  });
  return nodes;
}

interface MarkdownNoteEditorProps {
  disabled?: boolean;
  id?: string;
  maxLength?: number;
  onChange: (value: string) => void;
  value: string;
}

export function MarkdownNoteEditor({
  disabled = false,
  id = "note-body",
  maxLength = DEFAULT_MAX_LENGTH,
  onChange,
  value,
}: MarkdownNoteEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlightRef = useRef<HTMLPreElement>(null);
  const [plainText, setPlainText] = useState(false);
  const [limitError, setLimitError] = useState<string | null>(null);
  const formatter = useMemo(() => new Intl.NumberFormat("en-US"), []);
  const remaining = maxLength - value.length;

  let highlighted: ReactNode = value;
  let highlightingFailed = false;
  if (!plainText) {
    try {
      highlighted = highlightMarkdownSource(value);
    } catch {
      highlightingFailed = true;
    }
  }
  const usePlainText = plainText || highlightingFailed;

  function syncScroll() {
    const textarea = textareaRef.current;
    const overlay = highlightRef.current;
    if (!textarea || !overlay) return;
    overlay.scrollTop = textarea.scrollTop;
    overlay.scrollLeft = textarea.scrollLeft;
  }

  function replaceSelection(
    replacement: string,
    selectionStart: number,
    selectionEnd: number,
  ) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const nextLength =
      textarea.value.length - (end - start) + replacement.length;
    if (nextLength > maxLength) {
      setLimitError(
        `That formatting would exceed the ${formatter.format(maxLength)}-character note limit.`,
      );
      return;
    }

    setLimitError(null);
    textarea.focus();
    let insertedWithUndo = false;
    try {
      insertedWithUndo =
        typeof document.execCommand === "function" &&
        document.execCommand("insertText", false, replacement);
    } catch {
      insertedWithUndo = false;
    }
    if (!insertedWithUndo) {
      textarea.setRangeText(replacement, start, end, "end");
    }
    onChange(textarea.value);
    textarea.setSelectionRange(selectionStart, selectionEnd);
    syncScroll();
  }

  function wrapSelection(marker: string, placeholder: string) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = textarea.value.slice(start, end) || placeholder;
    replaceSelection(
      `${marker}${selected}${marker}`,
      start + marker.length,
      start + marker.length + selected.length,
    );
  }

  function prefixSelectedLines(prefix: (index: number) => string) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const lineStart =
      textarea.value.lastIndexOf("\n", Math.max(0, start - 1)) + 1;
    const nextBreak = textarea.value.indexOf("\n", end);
    const lineEnd = nextBreak === -1 ? textarea.value.length : nextBreak;
    textarea.setSelectionRange(lineStart, lineEnd);
    const replacement = textarea.value
      .slice(lineStart, lineEnd)
      .split("\n")
      .map((line, index) => `${prefix(index)}${line}`)
      .join("\n");
    replaceSelection(replacement, lineStart, lineStart + replacement.length);
  }

  function insertLink() {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value.slice(start, end) || "link text";
    const replacement = `[${text}](https://)`;
    replaceSelection(replacement, start + 1, start + 1 + text.length);
  }

  function insertCodeBlock() {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const code = textarea.value.slice(start, end) || "code";
    const replacement = `\`\`\`\n${code}\n\`\`\``;
    replaceSelection(replacement, start + 4, start + 4 + code.length);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
    const key = event.key.toLowerCase();
    if (key === "b") {
      event.preventDefault();
      wrapSelection("**", "bold text");
    } else if (key === "i") {
      event.preventDefault();
      wrapSelection("_", "italic text");
    }
  }

  return (
    <div className={`markdown-editor${usePlainText ? " plain-text" : ""}`}>
      <div
        aria-label="Markdown formatting"
        className="markdown-editor-toolbar"
        role="toolbar"
      >
        <button
          aria-label="Bold (Ctrl or Command+B)"
          disabled={disabled}
          onClick={() => wrapSelection("**", "bold text")}
          onMouseDown={(event) => event.preventDefault()}
          title="Bold (Ctrl/Cmd+B)"
          type="button"
        >
          <strong>B</strong>
        </button>
        <button
          aria-label="Italic (Ctrl or Command+I)"
          disabled={disabled}
          onClick={() => wrapSelection("_", "italic text")}
          onMouseDown={(event) => event.preventDefault()}
          title="Italic (Ctrl/Cmd+I)"
          type="button"
        >
          <em>I</em>
        </button>
        <button
          aria-label="Heading"
          disabled={disabled}
          onClick={() => prefixSelectedLines(() => "# ")}
          onMouseDown={(event) => event.preventDefault()}
          title="Heading"
          type="button"
        >
          H
        </button>
        <button
          aria-label="Bulleted list"
          disabled={disabled}
          onClick={() => prefixSelectedLines(() => "- ")}
          onMouseDown={(event) => event.preventDefault()}
          title="Bulleted list"
          type="button"
        >
          • List
        </button>
        <button
          aria-label="Numbered list"
          disabled={disabled}
          onClick={() => prefixSelectedLines((index) => `${index + 1}. `)}
          onMouseDown={(event) => event.preventDefault()}
          title="Numbered list"
          type="button"
        >
          1. List
        </button>
        <button
          aria-label="Blockquote"
          disabled={disabled}
          onClick={() => prefixSelectedLines(() => "> ")}
          onMouseDown={(event) => event.preventDefault()}
          title="Blockquote"
          type="button"
        >
          “ Quote
        </button>
        <button
          aria-label="Link"
          disabled={disabled}
          onClick={insertLink}
          onMouseDown={(event) => event.preventDefault()}
          title="Link"
          type="button"
        >
          Link
        </button>
        <button
          aria-label="Inline code"
          disabled={disabled}
          onClick={() => wrapSelection("`", "code")}
          onMouseDown={(event) => event.preventDefault()}
          title="Inline code"
          type="button"
        >
          Code
        </button>
        <button
          aria-label="Code block"
          disabled={disabled}
          onClick={insertCodeBlock}
          onMouseDown={(event) => event.preventDefault()}
          title="Code block"
          type="button"
        >
          ```
        </button>
        <span className="markdown-editor-toolbar-spacer" />
        <button
          aria-label={
            plainText
              ? "Turn syntax highlighting on"
              : "Use plain-text fallback"
          }
          aria-pressed={plainText}
          className="markdown-editor-fallback"
          disabled={disabled}
          onClick={() => setPlainText((current) => !current)}
          type="button"
        >
          {plainText ? "Highlight syntax" : "Plain text"}
        </button>
      </div>

      <div className="markdown-editor-surface">
        {!usePlainText && (
          <pre
            aria-hidden="true"
            className="markdown-editor-highlight"
            ref={highlightRef}
          >
            {highlighted}
            {value.endsWith("\n") ? "\n" : null}
          </pre>
        )}
        <textarea
          aria-describedby={`${id}-status`}
          aria-label="Note body"
          className="markdown-editor-input"
          disabled={disabled}
          id={id}
          maxLength={maxLength}
          onChange={(event) => {
            setLimitError(null);
            onChange(event.target.value);
          }}
          onKeyDown={handleKeyDown}
          onScroll={syncScroll}
          placeholder="Write in plain text or Markdown…"
          ref={textareaRef}
          rows={10}
          spellCheck="true"
          value={value}
        />
      </div>

      <div
        className={`markdown-editor-status${remaining <= 1000 ? " near-limit" : ""}`}
        id={`${id}-status`}
      >
        <span>
          {usePlainText
            ? "Plain-text editing mode. Markdown is still stored exactly as typed."
            : "Markdown characters stay visible while their meaning is highlighted."}
        </span>
        <span aria-live="polite">
          {formatter.format(value.length)} / {formatter.format(maxLength)}{" "}
          characters
        </span>
      </div>
      {limitError && (
        <p className="markdown-editor-limit-error" role="alert">
          {limitError}
        </p>
      )}
    </div>
  );
}
