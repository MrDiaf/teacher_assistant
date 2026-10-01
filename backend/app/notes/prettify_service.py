from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.courses.errors import InvalidNotePrettifyResponseError, NotePrettifyInputTooLargeError
from app.notes.prettify_schemas import NotePrettifyResponse
from app.platform.ai import AiModelRegistry, CodexAdapter, create_prettify_workspace

MAX_PRETTIFY_CHARACTERS = 40_000


class _GeneratedPrettifySuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_body: str = Field(max_length=MAX_PRETTIFY_CHARACTERS)


PRETTIFY_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "proposed_body": {
            "type": "string",
            "maxLength": MAX_PRETTIFY_CHARACTERS,
        }
    },
    "required": ["proposed_body"],
}


@dataclass(frozen=True)
class _MarkdownSnapshot:
    line_prefixes: tuple[str, ...]
    inline_markers: tuple[str, ...]
    protected_content: tuple[str, ...]


_LINE_PREFIX = re.compile(r"^(\s{0,3}(?:#{1,6}(?=\s)|>|[-+*](?=\s)|\d+[.)](?=\s))\s*)")
_HORIZONTAL_RULE = re.compile(r"^\s{0,3}(?:(?:-\s*){3,}|(?:\*\s*){3,}|(?:_\s*){3,})$")
_INLINE_MARKER = re.compile(r"\*\*|__|~~|(?<!\*)\*(?!\*)|(?<!_)_(?!_)|!?\[|\]\(")
_INLINE_CODE = re.compile(r"(`+)([^`\n]*?)\1")
_BRACKETED_CONTENT = re.compile(r"!?\[[^\]\n]+\](?:\[[^\]\n]*\]|\([^)\n]*\))?")
_BARE_URL = re.compile(r"https?://[^\s<>\]\)]+")
_FORMULA = re.compile(r"(?<!\\)(\${1,2})(.+?)(?<!\\)\1")
_LATEX_FORMULA = re.compile(r"\\\([^\n]+?\\\)|\\\[[^\n]+?\\\]")
_AUTHOR_DATE_CITATION = re.compile(
    r"\([A-Z][^()\n]{0,80},\s*(?:19|20)\d{2}[a-z]?(?:;[^()\n]{1,80})?\)"
)
_QUOTED = re.compile(r'("[^"\n]+"|“[^”\n]+”|‘[^’\n]+’|(?<!\w)\'[^\'\n]+\'(?!\w))')
_FENCE_OPEN = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def _fenced_blocks(value: str) -> tuple[list[str], set[int]]:
    lines = value.splitlines(keepends=True)
    blocks: list[str] = []
    protected_lines: set[int] = set()
    index = 0
    while index < len(lines):
        match = _FENCE_OPEN.match(lines[index])
        if match is None:
            index += 1
            continue
        marker = match.group(1)
        start = index
        index += 1
        closing = re.compile(rf"^\s{{0,3}}{re.escape(marker[0])}{{{len(marker)},}}\s*$")
        while index < len(lines):
            if closing.match(lines[index].rstrip("\r\n")):
                index += 1
                break
            index += 1
        protected_lines.update(range(start, index))
        blocks.append("".join(lines[start:index]))
    return blocks, protected_lines


def _markdown_snapshot(value: str) -> _MarkdownSnapshot:
    blocks, protected_lines = _fenced_blocks(value)
    lines = value.splitlines()
    line_prefixes: list[str] = []
    inspectable_lines: list[str] = []
    for index, line in enumerate(lines):
        if index in protected_lines:
            line_prefixes.append("<code>")
            continue
        match = _LINE_PREFIX.match(line)
        line_prefixes.append(
            line if _HORIZONTAL_RULE.match(line) else match.group(1) if match else ""
        )
        inspectable_lines.append(line)
    inspectable = "\n".join(inspectable_lines)
    protected: list[str] = [*blocks]
    for pattern in (
        _INLINE_CODE,
        _BRACKETED_CONTENT,
        _BARE_URL,
        _FORMULA,
        _LATEX_FORMULA,
        _AUTHOR_DATE_CITATION,
        _QUOTED,
    ):
        protected.extend(match.group(0) for match in pattern.finditer(inspectable))
    return _MarkdownSnapshot(
        line_prefixes=tuple(line_prefixes),
        inline_markers=tuple(_INLINE_MARKER.findall(inspectable)),
        protected_content=tuple(protected),
    )


def parse_and_validate_prettify(raw_response: str | None, original: str) -> str:
    if raw_response is None:
        raise InvalidNotePrettifyResponseError()
    try:
        parsed = _GeneratedPrettifySuggestion.model_validate(json.loads(raw_response))
        parsed.proposed_body.encode("utf-8", errors="strict")
    except (json.JSONDecodeError, UnicodeError, ValidationError, TypeError) as exc:
        raise InvalidNotePrettifyResponseError() from exc

    proposed = parsed.proposed_body
    if "\x00" in proposed or proposed.count("\n") != original.count("\n"):
        raise InvalidNotePrettifyResponseError()
    if _markdown_snapshot(proposed) != _markdown_snapshot(original):
        raise InvalidNotePrettifyResponseError()
    return proposed


class NotePrettifyService:
    def __init__(self, adapter: CodexAdapter) -> None:
        self.adapter = adapter
        self.models = AiModelRegistry()

    async def suggest(self, body: str, requested_model: str | None) -> NotePrettifyResponse:
        model = self.models.resolve(requested_model)
        try:
            body.encode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise InvalidNotePrettifyResponseError() from exc
        if len(body) > MAX_PRETTIFY_CHARACTERS:
            raise NotePrettifyInputTooLargeError(MAX_PRETTIFY_CHARACTERS)
        if not body.strip():
            return NotePrettifyResponse(
                proposed_body=body,
                has_changes=False,
                message="No clear corrections were found.",
                model=model,
            )

        with create_prettify_workspace(
            draft=body,
            output_schema=PRETTIFY_OUTPUT_SCHEMA,
        ) as workspace:
            result = await self.adapter.answer(workspace, model=model)
            proposed = parse_and_validate_prettify(result.final_response, body)
        changed = proposed != body
        return NotePrettifyResponse(
            proposed_body=proposed,
            has_changes=changed,
            message=(
                "Review every proposed change before using this draft."
                if changed
                else "No clear corrections were found."
            ),
            model=model,
        )
