import hashlib
import json
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codex_runtime.adapter import (
    CodexRuntimeResult,
    get_codex_adapter,
)
from app.core.errors import AssistantRuntimeError, InvalidNoteSummaryResponseError
from app.course_sources.models import ExtractedSourceText
from app.main import app
from app.notes.summary_models import NoteSummary
from app.notes.summary_validation import parse_and_validate_summary
from tests.helpers import create_course, create_note, upload_course_source


class FakeSummaryCodexAdapter:
    def __init__(self) -> None:
        self.response: str | None = None
        self.fail_with: AssistantRuntimeError | None = None
        self.calls: list[dict[str, Any]] = []

    async def answer(self, workspace, model=None) -> CodexRuntimeResult:
        snapshot = {
            "root": workspace.root,
            "model": model,
            "note": json.loads((workspace.job_directory / "NOTE.json").read_text()),
            "slides": json.loads((workspace.job_directory / "LINKED_SLIDES.json").read_text()),
            "schema": json.loads((workspace.job_directory / "OUTPUT_SCHEMA.json").read_text()),
            "files": sorted(
                str(path.relative_to(workspace.job_directory))
                for path in workspace.job_directory.rglob("*")
            ),
            "prompt": workspace.prompt,
        }
        self.calls.append(snapshot)
        if self.fail_with:
            raise self.fail_with
        return CodexRuntimeResult(final_response=self.response)


@pytest.fixture
def fake_summary_codex() -> Iterator[FakeSummaryCodexAdapter]:
    adapter = FakeSummaryCodexAdapter()
    app.dependency_overrides[get_codex_adapter] = lambda: adapter
    try:
        yield adapter
    finally:
        app.dependency_overrides.pop(get_codex_adapter, None)


def summary_payload(
    *,
    note_id: str,
    source_id: str | None = None,
    slide: int = 1,
) -> str:
    bullets: list[dict[str, Any]] = [
        {
            "text": "The note highlights transaction isolation.",
            "origin": "note",
            "source_references": [{"note_id": note_id, "source_id": None, "slide": None}],
        }
    ]
    if source_id:
        bullets.extend(
            [
                {
                    "text": "The linked slide defines serializability.",
                    "origin": "slide",
                    "source_references": [
                        {
                            "note_id": None,
                            "source_id": source_id,
                            "slide": slide,
                        }
                    ],
                },
                {
                    "text": "Together they connect isolation with serial execution.",
                    "origin": "mixed",
                    "source_references": [
                        {"note_id": note_id, "source_id": None, "slide": None},
                        {
                            "note_id": None,
                            "source_id": source_id,
                            "slide": slide,
                        },
                    ],
                },
            ]
        )
    return json.dumps({"bullets": bullets})


async def test_model_endpoint_is_server_authoritative_and_assistant_rejects_unknown_model(
    client: AsyncClient,
    fake_summary_codex: FakeSummaryCodexAdapter,
) -> None:
    models = await client.get("/api/v1/ai/models")
    assert models.status_code == 200
    assert models.json()["default_model"] == "gpt-5.6-sol"
    assert [item["id"] for item in models.json()["models"]] == [
        "gpt-5.6-sol",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
    ]

    conversation = await client.post(
        "/api/v1/assistant/conversations",
        json={"title": "Calendar conversation"},
    )
    rejected = await client.post(
        f"/api/v1/assistant/conversations/{conversation.json()['id']}/messages",
        json={"content": "What is tomorrow?", "model": "browser-invented-model"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "invalid_ai_model"
    assert fake_summary_codex.calls == []

    course = await create_course(client)
    note = await create_note(client, course["id"])
    rejected_summary = await client.post(
        f"/api/v1/notes/{note['id']}/summaries",
        json={"model": "browser-invented-model"},
    )
    assert rejected_summary.status_code == 400
    assert rejected_summary.json()["code"] == "invalid_ai_model"
    assert fake_summary_codex.calls == []


def test_summary_parser_rejects_hidden_reasoning() -> None:
    note_id = uuid.uuid4()
    with pytest.raises(InvalidNoteSummaryResponseError):
        parse_and_validate_summary(
            json.dumps(
                {
                    "bullets": [
                        {
                            "text": "A valid-looking bullet.",
                            "origin": "note",
                            "source_references": [
                                {
                                    "note_id": str(note_id),
                                    "source_id": None,
                                    "slide": None,
                                }
                            ],
                        }
                    ],
                    "reasoning": "This must never be stored.",
                }
            ),
            note_id=note_id,
            note_available=True,
            available_slides=set(),
        )


async def test_summary_uses_only_note_and_explicit_linked_slides_with_provenance(
    client: AsyncClient,
    fake_summary_codex: FakeSummaryCodexAdapter,
) -> None:
    course = await create_course(client)
    linked = await upload_course_source(
        client,
        course["id"],
        file_name="linked.txt",
        content=b"Serializability means equivalent serial execution.",
        source_type="slides",
        display_name="Transactions slides",
    )
    await upload_course_source(
        client,
        course["id"],
        file_name="private-reading.txt",
        content=b"UNRELATED LITERATURE SECRET",
        source_type="literature",
    )
    await upload_course_source(
        client,
        course["id"],
        file_name="unlinked.txt",
        content=b"UNLINKED SLIDE SECRET",
        source_type="slides",
    )
    note = await create_note(
        client,
        course["id"],
        body="Transaction isolation prevents conflicting changes.",
        slide_references=[
            {
                "source_id": linked["id"],
                "start_slide": 1,
                "end_slide": 1,
                "label": "Core concept",
            }
        ],
    )
    fake_summary_codex.response = summary_payload(
        note_id=note["id"],
        source_id=linked["id"],
    )

    generated = await client.post(
        f"/api/v1/notes/{note['id']}/summaries",
        json={"model": "gpt-5.6-terra"},
    )

    assert generated.status_code == 201, generated.text
    body = generated.json()
    assert body["status"] == "completed"
    assert body["model"] == "gpt-5.6-terra"
    assert [bullet["origin"] for bullet in body["summary_json"]["bullets"]] == [
        "note",
        "slide",
        "mixed",
    ]
    assert all(
        uuid.UUID(bullet["id"]) for bullet in body["summary_json"]["bullets"]
    )
    assert len(body["note_content_hash"]) == 64
    assert len(body["slide_content_hash"]) == 64

    assert len(fake_summary_codex.calls) == 1
    call = fake_summary_codex.calls[0]
    assert call["model"] == "gpt-5.6-terra"
    assert call["note"] == {
        "id": note["id"],
        "body": "Transaction isolation prevents conflicting changes.",
    }
    assert call["slides"] == [
        {
            "source_id": linked["id"],
            "slide": 1,
            "text": "Serializability means equivalent serial execution.",
        }
    ]
    serialized_call = json.dumps(call, default=str)
    assert "UNRELATED LITERATURE SECRET" not in serialized_call
    assert "UNLINKED SLIDE SECRET" not in serialized_call
    assert set(call["files"]) == {
        "AGENT.md",
        "LINKED_SLIDES.json",
        "NOTE.json",
        "OUTPUT",
        "OUTPUT_SCHEMA.json",
    }
    assert "hidden reasoning" in call["prompt"]
    assert "id" not in call["schema"]["properties"]["bullets"]["items"]["properties"]
    assert not Path(call["root"]).exists()

    latest = await client.get(f"/api/v1/notes/{note['id']}/summary")
    assert latest.status_code == 200
    assert latest.json()["id"] == body["id"]
    assert latest.json()["is_stale"] is False


@pytest.mark.parametrize(
    "invalid_bullet",
    [
        {
            "text": "Unknown origin",
            "origin": "book",
            "source_references": [],
        },
        {
            "text": "Invented note",
            "origin": "note",
            "source_references": [
                {
                    "note_id": str(uuid.uuid4()),
                    "source_id": None,
                    "slide": None,
                }
            ],
        },
        {
            "text": "Origin does not match references",
            "origin": "mixed",
            "source_references": [],
        },
    ],
)
async def test_invalid_summary_origins_and_references_fail_closed(
    client: AsyncClient,
    fake_summary_codex: FakeSummaryCodexAdapter,
    invalid_bullet: dict[str, Any],
) -> None:
    course = await create_course(client)
    note = await create_note(client, course["id"])
    fake_summary_codex.response = json.dumps({"bullets": [invalid_bullet]})

    response = await client.post(
        f"/api/v1/notes/{note['id']}/summaries",
        json={"model": "gpt-5.6-sol"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["safe_error_code"] == "invalid_note_summary_response"
    assert response.json()["summary_json"] is None


async def test_summary_becomes_stale_after_note_or_linked_slide_text_changes(
    client: AsyncClient,
    session: AsyncSession,
    fake_summary_codex: FakeSummaryCodexAdapter,
) -> None:
    course = await create_course(client)
    slides = await upload_course_source(
        client,
        course["id"],
        file_name="deck.txt",
        content=b"Original slide text",
        source_type="slides",
    )
    note = await create_note(
        client,
        course["id"],
        slide_references=[
            {
                "source_id": slides["id"],
                "start_slide": None,
                "end_slide": None,
            }
        ],
    )
    fake_summary_codex.response = summary_payload(
        note_id=note["id"],
        source_id=slides["id"],
    )
    created = await client.post(
        f"/api/v1/notes/{note['id']}/summaries",
        json={"model": "gpt-5.6-sol"},
    )
    assert created.json()["status"] == "completed"

    changed_note = await client.patch(
        f"/api/v1/notes/{note['id']}",
        json={"body": "Changed note body"},
    )
    assert changed_note.status_code == 200
    stale_note = await client.get(f"/api/v1/notes/{note['id']}/summary")
    assert stale_note.json()["is_stale"] is True

    await client.patch(
        f"/api/v1/notes/{note['id']}",
        json={"body": "Important course ideas."},
    )
    extracted = await session.scalar(
        select(ExtractedSourceText).where(ExtractedSourceText.source_id == uuid.UUID(slides["id"]))
    )
    assert extracted is not None
    extracted.text = "Changed slide text"
    extracted.content_hash = hashlib.sha256(extracted.text.encode()).hexdigest()
    await session.commit()

    stale_slide = await client.get(f"/api/v1/notes/{note['id']}/summary")
    assert stale_slide.json()["is_stale"] is True


async def test_failed_summary_can_retry_with_same_stored_model(
    client: AsyncClient,
    fake_summary_codex: FakeSummaryCodexAdapter,
) -> None:
    course = await create_course(client)
    note = await create_note(client, course["id"])
    fake_summary_codex.fail_with = AssistantRuntimeError("The model is temporarily unavailable.")

    failed = await client.post(
        f"/api/v1/notes/{note['id']}/summaries",
        json={"model": "gpt-5.6-luna"},
    )
    assert failed.status_code == 201
    assert failed.json()["status"] == "failed"
    assert failed.json()["model"] == "gpt-5.6-luna"

    fake_summary_codex.fail_with = None
    fake_summary_codex.response = summary_payload(note_id=note["id"])
    retried = await client.post(f"/api/v1/note-summaries/{failed.json()['id']}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "completed"
    assert retried.json()["id"] == failed.json()["id"]
    assert fake_summary_codex.calls[-1]["model"] == "gpt-5.6-luna"

    repeated = await client.post(f"/api/v1/note-summaries/{failed.json()['id']}/retry")
    assert repeated.status_code == 409
    assert repeated.json()["code"] == "note_summary_not_retryable"


async def test_unavailable_linked_text_fails_safely_without_calling_codex(
    client: AsyncClient,
    fake_summary_codex: FakeSummaryCodexAdapter,
) -> None:
    course = await create_course(client)
    slides = await upload_course_source(
        client,
        course["id"],
        file_name="images.bin",
        content=b"\x01\x02image-only",
        source_type="slides",
    )
    note = await create_note(
        client,
        course["id"],
        slide_references=[
            {
                "source_id": slides["id"],
                "start_slide": None,
                "end_slide": None,
            }
        ],
    )

    response = await client.post(
        f"/api/v1/notes/{note['id']}/summaries",
        json={"model": "gpt-5.6-sol"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["safe_error_code"] == "note_summary_source_unavailable"
    assert "Linked slide text is unavailable" in response.json()["safe_error"]
    assert fake_summary_codex.calls == []


async def test_removing_one_summary_bullet_is_exact_persistent_and_safely_repeatable(
    client: AsyncClient,
    fake_summary_codex: FakeSummaryCodexAdapter,
) -> None:
    course = await create_course(client)
    slides = await upload_course_source(
        client,
        course["id"],
        file_name="deck.txt",
        content=b"Serializable schedules preserve transaction behavior.",
        source_type="slides",
    )
    note = await create_note(
        client,
        course["id"],
        body="Isolation prevents unsafe interleavings.",
        slide_references=[
            {
                "source_id": slides["id"],
                "start_slide": 1,
                "end_slide": 1,
            }
        ],
    )
    fake_summary_codex.response = summary_payload(
        note_id=note["id"],
        source_id=slides["id"],
    )
    generated = await client.post(
        f"/api/v1/notes/{note['id']}/summaries",
        json={"model": "gpt-5.6-sol"},
    )
    original = generated.json()["summary_json"]["bullets"]
    removed_id = original[1]["id"]

    removed = await client.delete(
        f"/api/v1/note-summaries/{generated.json()['id']}/bullets/{removed_id}"
    )

    assert removed.status_code == 200, removed.text
    remaining = removed.json()["summary_json"]["bullets"]
    assert remaining == [original[0], original[2]]
    latest = await client.get(f"/api/v1/notes/{note['id']}/summary")
    assert latest.json()["summary_json"]["bullets"] == remaining

    repeated = await client.delete(
        f"/api/v1/note-summaries/{generated.json()['id']}/bullets/{removed_id}"
    )
    assert repeated.status_code == 409
    assert repeated.json()["code"] == "note_summary_bullet_not_found"
    assert (await client.get(f"/api/v1/notes/{note['id']}/summary")).json()[
        "summary_json"
    ]["bullets"] == remaining

    for bullet in remaining:
        deleted = await client.delete(
            f"/api/v1/note-summaries/{generated.json()['id']}/bullets/{bullet['id']}"
        )
        assert deleted.status_code == 200
    final = await client.get(f"/api/v1/notes/{note['id']}/summary")
    assert final.json()["summary_json"] == {"bullets": []}
    assert (await client.get(f"/api/v1/notes/{note['id']}")).status_code == 200


async def test_legacy_summary_bullets_receive_persisted_backend_ids(
    client: AsyncClient,
    session: AsyncSession,
    fake_summary_codex: FakeSummaryCodexAdapter,
) -> None:
    course = await create_course(client)
    note = await create_note(client, course["id"])
    fake_summary_codex.response = summary_payload(note_id=note["id"])
    generated = await client.post(
        f"/api/v1/notes/{note['id']}/summaries",
        json={"model": "gpt-5.6-sol"},
    )
    summary = await session.get(NoteSummary, uuid.UUID(generated.json()["id"]))
    assert summary is not None
    legacy_bullets = [
        {key: value for key, value in bullet.items() if key != "id"}
        for bullet in summary.summary_json["bullets"]
    ]
    summary.summary_json = {"bullets": legacy_bullets}
    await session.commit()

    first = await client.get(f"/api/v1/notes/{note['id']}/summary")
    first_id = first.json()["summary_json"]["bullets"][0]["id"]
    assert uuid.UUID(first_id)
    second = await client.get(f"/api/v1/notes/{note['id']}/summary")
    assert second.json()["summary_json"]["bullets"][0]["id"] == first_id


async def test_bullets_cannot_be_removed_from_failed_summary(
    client: AsyncClient,
    fake_summary_codex: FakeSummaryCodexAdapter,
) -> None:
    course = await create_course(client)
    note = await create_note(client, course["id"])
    fake_summary_codex.fail_with = AssistantRuntimeError("Unavailable")
    failed = await client.post(
        f"/api/v1/notes/{note['id']}/summaries",
        json={"model": "gpt-5.6-sol"},
    )

    response = await client.delete(
        f"/api/v1/note-summaries/{failed.json()['id']}/bullets/{uuid.uuid4()}"
    )
    assert response.status_code == 409
    assert response.json()["code"] == "note_summary_not_editable"
