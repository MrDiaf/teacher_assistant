import { createElement, type ReactNode } from "react";

const INLINE_MARKDOWN =
  /(`([^`\n]+)`)|(\[([^\]\n]+)\]\(([^)\n]*)\))|(\*\*([^*\n]+)\*\*)|(__([^_\n]+)__)|(\*([^*\n]+)\*)|(_([^_\n]+)_)/g;

function safeLinkTarget(rawTarget: string): string | null {
  const target = rawTarget.trim();
  if (!target) return null;
  const compact = target.replace(/[\u0000-\u0020\u007f]+/g, "").toLowerCase();
  if (
    compact.startsWith("javascript:") ||
    compact.startsWith("vbscript:") ||
    compact.startsWith("data:") ||
    compact.startsWith("file:")
  ) {
    return null;
  }
  const scheme = compact.match(/^([a-z][a-z0-9+.-]*):/);
  if (scheme && !["http", "https", "mailto"].includes(scheme[1])) {
    return null;
  }
  return target;
}

export function renderSafeMarkdownInline(
  source: string,
  keyPrefix: string,
): ReactNode[] {
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let token = 0;

  for (const match of source.matchAll(INLINE_MARKDOWN)) {
    const index = match.index ?? 0;
    if (index > cursor) nodes.push(source.slice(cursor, index));
    const key = `${keyPrefix}-${token}`;
    token += 1;

    if (match[1]) {
      nodes.push(<code key={key}>{match[2]}</code>);
    } else if (match[3]) {
      const href = safeLinkTarget(match[5]);
      nodes.push(
        href ? (
          <a href={href} key={key} rel="nofollow noopener noreferrer">
            {match[4]}
          </a>
        ) : (
          <span
            aria-label={`${match[4]} (unsafe link removed)`}
            className="safe-markdown-unsafe-link"
            key={key}
            title="Unsafe link removed"
          >
            {match[4]}
          </span>
        ),
      );
    } else if (match[6] || match[8]) {
      nodes.push(<strong key={key}>{match[7] ?? match[9]}</strong>);
    } else {
      nodes.push(<em key={key}>{match[11] ?? match[13]}</em>);
    }
    cursor = index + match[0].length;
  }

  if (cursor < source.length) nodes.push(source.slice(cursor));
  return nodes;
}

function inlineWithBreaks(lines: string[], keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  lines.forEach((line, index) => {
    nodes.push(...renderSafeMarkdownInline(line, `${keyPrefix}-${index}`));
    if (index < lines.length - 1)
      nodes.push(<br key={`${keyPrefix}-break-${index}`} />);
  });
  return nodes;
}

function startsBlock(line: string) {
  return (
    /^\s*```/.test(line) ||
    /^\s{0,3}#{1,6}\s+/.test(line) ||
    /^\s*>\s?/.test(line) ||
    /^\s*[-+*]\s+/.test(line) ||
    /^\s*\d+[.)]\s+/.test(line)
  );
}

export function renderSafeMarkdownBlocks(source: string): ReactNode[] {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;
  let block = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }
    const key = `markdown-block-${block}`;
    block += 1;

    const fence = line.match(/^\s*```([A-Za-z0-9_-]*)\s*$/);
    if (fence) {
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
        code.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push(
        <pre className="safe-markdown-code-block" key={key}>
          <code data-language={fence[1] || undefined}>{code.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    const heading = line.match(/^\s{0,3}(#{1,6})\s+(.*)$/);
    if (heading) {
      const sourceLevel = heading[1].length;
      const renderedLevel = Math.min(6, sourceLevel + 3) as 4 | 5 | 6;
      blocks.push(
        createElement(
          `h${renderedLevel}`,
          { className: `safe-markdown-heading level-${sourceLevel}`, key },
          renderSafeMarkdownInline(heading[2], `${key}-heading`),
        ),
      );
      index += 1;
      continue;
    }

    const unordered = line.match(/^\s*[-+*]\s+(.*)$/);
    if (unordered) {
      const items: string[] = [];
      while (index < lines.length) {
        const item = lines[index].match(/^\s*[-+*]\s+(.*)$/);
        if (!item) break;
        items.push(item[1]);
        index += 1;
      }
      blocks.push(
        <ul key={key}>
          {items.map((item, itemIndex) => (
            <li key={`${key}-${itemIndex}`}>
              {renderSafeMarkdownInline(item, `${key}-${itemIndex}`)}
            </li>
          ))}
        </ul>,
      );
      continue;
    }

    const ordered = line.match(/^\s*(\d+)[.)]\s+(.*)$/);
    if (ordered) {
      const start = Number(ordered[1]);
      const items: string[] = [];
      while (index < lines.length) {
        const item = lines[index].match(/^\s*\d+[.)]\s+(.*)$/);
        if (!item) break;
        items.push(item[1]);
        index += 1;
      }
      blocks.push(
        <ol key={key} start={start}>
          {items.map((item, itemIndex) => (
            <li key={`${key}-${itemIndex}`}>
              {renderSafeMarkdownInline(item, `${key}-${itemIndex}`)}
            </li>
          ))}
        </ol>,
      );
      continue;
    }

    const quote = line.match(/^\s*>\s?(.*)$/);
    if (quote) {
      const quotedLines: string[] = [];
      while (index < lines.length) {
        const quoted = lines[index].match(/^\s*>\s?(.*)$/);
        if (!quoted) break;
        quotedLines.push(quoted[1]);
        index += 1;
      }
      blocks.push(
        <blockquote key={key}>
          <p>{inlineWithBreaks(quotedLines, `${key}-quote`)}</p>
        </blockquote>,
      );
      continue;
    }

    const paragraph: string[] = [line];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !startsBlock(lines[index])
    ) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push(
      <p key={key}>{inlineWithBreaks(paragraph, `${key}-paragraph`)}</p>,
    );
  }

  return blocks;
}

export function SafeMarkdown({
  className = "",
  source,
}: {
  className?: string;
  source: string;
}) {
  let content: ReactNode;
  try {
    content = renderSafeMarkdownBlocks(source);
  } catch {
    content = <p>{source}</p>;
  }
  return <div className={`safe-markdown ${className}`.trim()}>{content}</div>;
}
