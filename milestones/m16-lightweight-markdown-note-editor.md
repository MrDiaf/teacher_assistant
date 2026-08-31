# M16 — Lightweight Markdown note editor

- [x] This milestone

## Outcome

Replace the plain note-body textarea with a lightweight Markdown-aware editor
that keeps the Markdown characters visible while also styling their meaning.
For example, the owner should still see the `**` characters in `**text**` while
the word `text` is visually bold.

The stored note body remains ordinary Markdown text. This is not a rich-text
document format migration.

## Editor requirements

- Keep raw Markdown syntax visible and directly editable.
- Visually distinguish at least headings, bold, italic, unordered and ordered
  lists, blockquotes, links, inline code, and fenced code blocks.
- Provide a small toolbar for common formatting such as bold, italic, heading,
  list, link, and code.
- Preserve caret/selection position, browser/editor undo-redo, copy/paste, and
  keyboard text entry.
- Support familiar keyboard shortcuts such as Ctrl/Cmd+B and Ctrl/Cmd+I.
- Keep the existing 100,000-character backend limit and show a usable character
  or validation state near the limit.
- Retain a reliable plain-text fallback if syntax highlighting cannot load.
- Do not add collaboration, comments, document pages, or a full office-style
  editor.

The implementation may use a focused editor library or a tested custom
component, but it must not hide syntax markers in a WYSIWYG-only model.

## Safe Markdown display

Note cards should render supported Markdown instead of displaying the body as
one plain paragraph. Rendering must:

- disable or strip raw HTML;
- sanitize links and reject unsafe schemes such as `javascript:`;
- prevent script execution, event-handler injection, iframes, and arbitrary
  embedded content;
- preserve readable plain text when syntax is malformed;
- use semantic headings/lists/code elements without breaking the surrounding
  page hierarchy;
- remain accessible without relying only on syntax color.

Storage, API schemas, slide references, summary staleness hashes, and note
ownership rules must continue to operate on the original Markdown string.

## Completed checklist

- [x] Select and document the minimal Markdown editor/rendering approach.
- [x] Add the Markdown-aware note-body editor with visible syntax characters.
- [x] Add the lightweight formatting toolbar and keyboard shortcuts.
- [x] Render supported Markdown safely on note cards.
- [x] Preserve raw Markdown exactly through create/edit/save/reopen.
- [x] Preserve slide-reference editing and validation.
- [x] Add plain-text fallback and readable loading/error behavior.
- [x] Add accessibility labels, focus behavior, and keyboard tests.
- [x] Add XSS, unsafe-link, malformed-Markdown, and round-trip tests.
- [x] Add responsive styling without redesigning the Course module.
- [x] Update note-format help text and documentation.

## Acceptance criteria

- Editing `**jere**` shows both pairs of stars and visually bolds `jere`.
- Saving and reopening a note returns the exact Markdown source characters.
- Supported Markdown renders readably on the note card.
- Raw HTML, scripts, unsafe links, and embedded active content cannot execute.
- Toolbar and keyboard operations preserve selection and undo behavior.
- Notes with no Markdown remain normal readable plain text.
- Existing slide links, summary generation, staleness detection, and note CRUD
  continue to work.
- Relevant frontend/backend regression tests, accessibility checks, lint, and
  production build pass.

## Expected implementation areas

```text
frontend/package.json and lockfile, only if a focused dependency is justified
frontend/src/features/courses/NoteDialog.tsx
frontend/src/features/courses/CourseNotes.tsx
frontend/src/features/courses/MarkdownNoteEditor.tsx
frontend/src/features/courses/SafeMarkdown.tsx
frontend/src/styles.css
frontend Courses tests and E2E coverage
README.md
```

Codex spelling correction belongs to M18, not this editor milestone.
