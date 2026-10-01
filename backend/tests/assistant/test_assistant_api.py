import asyncio
import json
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import AssistantContextAudit, AssistantProposal
from app.codex_runtime.adapter import (
    CodexAccountStatus,
    CodexDeviceLoginAttempt,
    CodexRuntimeResult,
    get_codex_adapter,
    get_codex_auth_manager,
)
from app.core.errors import AssistantRuntimeError
from tests.helpers import create_calendar, create_event


class FakeCodexAdapter:
    def __init__(self, response: str | None = None) -> None:
        self.response = response or json.dumps(
            {
                "message": "You have a planning session tomorrow from 10:00 to 11:00.",
                "proposal": None,
            }
        )
        self.calls: list[dict[str, Any]] = []
        self.fail_with: AssistantRuntimeError | None = None
        self.responses: list[str | None] = []
        self.started_event: asyncio.Event | None = None
        self.release_event: asyncio.Event | None = None

    async def answer(self, workspace, model=None) -> CodexRuntimeResult:
        def read_text(name: str) -> str | None:
            path = workspace.job_directory / name
            return path.read_text() if path.exists() else None

        def read_json(name: str, fallback):
            content = read_text(name)
            return json.loads(content) if content is not None else fallback

        snapshot = {
            "model": model,
            "root": workspace.root,
            "job_directory": workspace.job_directory,
            "policy": (workspace.job_directory / "AGENT.md").read_text(),
            "request": read_text("REQUEST.md"),
            "calendars": read_json("CALENDARS.json", []),
            "events": read_json("EVENTS.json", []),
            "courses": read_json("COURSES.json", []),
            "notes": read_json("NOTES.json", []),
            "slide_references": read_json("SLIDE_REFERENCES.json", []),
            "selected_slide_text": read_json("SELECTED_SLIDE_TEXT.json", []),
            "error_context": read_json("ERROR_CONTEXT.json", None),
            "schema": read_json("OUTPUT_SCHEMA.json", {}),
            "files": sorted(
                str(path.relative_to(workspace.job_directory))
                for path in workspace.job_directory.rglob("*")
            ),
        }
        self.calls.append(snapshot)
        if self.started_event is not None:
            self.started_event.set()
        if self.release_event is not None:
            await self.release_event.wait()
        if self.fail_with is not None:
            raise self.fail_with
        response = self.responses.pop(0) if self.responses else self.response
        return CodexRuntimeResult(final_response=response)


class FakeCodexAuth:
    def __init__(self) -> None:
        self.connected = False
        self.attempt = CodexDeviceLoginAttempt(
            login_id="login-123",
            verification_url="https://auth.openai.com/codex/device",
            user_code="ABCD-EFGH",
        )

    async def account_status(self) -> CodexAccountStatus:
        if not self.connected:
            return CodexAccountStatus(authenticated=False)
        return CodexAccountStatus(
            authenticated=True,
            auth_type="chatgpt",
            email="owner@example.test",
            plan_type="plus",
        )

    async def start_device_login(self) -> CodexDeviceLoginAttempt:
        return self.attempt

    async def get_device_login(self, login_id: str) -> CodexDeviceLoginAttempt:
        assert login_id == self.attempt.login_id
        self.connected = True
        self.attempt = replace(self.attempt, status="completed")
        return self.attempt

    async def logout(self) -> CodexAccountStatus:
        self.connected = False
        return await self.account_status()


@pytest.fixture
def fake_codex(host_app: FastAPI) -> Iterator[FakeCodexAdapter]:
    adapter = FakeCodexAdapter()
    host_app.dependency_overrides[get_codex_adapter] = lambda: adapter
    try:
        yield adapter
    finally:
        host_app.dependency_overrides.pop(get_codex_adapter, None)


@pytest.fixture
def fake_codex_auth(host_app: FastAPI) -> Iterator[FakeCodexAuth]:
    auth = FakeCodexAuth()
    host_app.dependency_overrides[get_codex_auth_manager] = lambda: auth
    try:
        yield auth
    finally:
        host_app.dependency_overrides.pop(get_codex_auth_manager, None)


async def create_conversation(client: AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/assistant/conversations",
        json={"title": "Calendar conversation"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def ask(
    client: AsyncClient,
    conversation_id: str,
    content: str,
    model: str | None = None,
):
    payload = {"content": content}
    if model is not None:
        payload["model"] = model
    return await client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/messages",
        json=payload,
    )


def upcoming_event_times() -> dict[str, str]:
    start = (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=10,
        minute=0,
        second=0,
        microsecond=0,
    )
    return {
        "start_at": start.isoformat(),
        "end_at": (start + timedelta(hours=1)).isoformat(),
    }


async def create_course_note_context(
    client: AsyncClient,
    *,
    course_name: str,
    course_code: str,
    note_title: str,
    note_body: str,
    slide_text: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    course_response = await client.post(
        "/api/v1/courses",
        json={
            "name": course_name,
            "course_code": course_code,
            "description": None,
            "term": "Autumn 2026",
            "color": "#29584c",
        },
    )
    assert course_response.status_code == 201, course_response.text
    course = course_response.json()
    source: dict[str, Any] | None = None
    references: list[dict[str, Any]] = []
    if slide_text is not None:
        source_response = await client.post(
            f"/api/v1/courses/{course['id']}/sources",
            params={
                "source_type": "slides",
                "file_name": f"{course_code.lower()}-slides.txt",
                "display_name": f"{course_name} lecture deck",
            },
            content=slide_text,
            headers={"Content-Type": "text/plain"},
        )
        assert source_response.status_code == 201, source_response.text
        source = source_response.json()
        references = [
            {
                "source_id": source["id"],
                "start_slide": 1,
                "end_slide": 1,
                "label": "Relevant lecture",
            }
        ]
    note_response = await client.post(
        f"/api/v1/courses/{course['id']}/notes",
        json={
            "title": note_title,
            "body": note_body,
            "slide_references": references,
        },
    )
    assert note_response.status_code == 201, note_response.text
    return course, note_response.json(), source


def assert_strict_object_schemas(node: Any) -> None:
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            assert node.get("additionalProperties") is False
            assert set(node.get("required", [])) == set(properties)
        for value in node.values():
            assert_strict_object_schemas(value)
    elif isinstance(node, list):
        for value in node:
            assert_strict_object_schemas(value)


async def test_chatgpt_device_login_exposes_only_safe_browser_details(
    client: AsyncClient,
    fake_codex_auth: FakeCodexAuth,
) -> None:
    signed_out = await client.get("/api/v1/ai/auth")
    started = await client.post("/api/v1/assistant/auth/device-code")
    completed = await client.get(
        f"/api/v1/ai/auth/device-code/{fake_codex_auth.attempt.login_id}"
    )
    signed_in = await client.get("/api/v1/assistant/auth")

    assert signed_out.status_code == 200
    assert signed_out.json() == {
        "authenticated": False,
        "auth_type": None,
        "email": None,
        "plan_type": None,
    }
    assert started.status_code == 201
    assert started.json() == {
        "login_id": "login-123",
        "verification_url": "https://auth.openai.com/codex/device",
        "user_code": "ABCD-EFGH",
        "status": "pending",
        "safe_error": None,
    }
    assert completed.json()["status"] == "completed"
    assert signed_in.json()["auth_type"] == "chatgpt"
    assert signed_in.json()["plan_type"] == "plus"
    assert "token" not in signed_in.text.lower()

    signed_out_again = await client.delete("/api/v1/ai/auth")
    assert signed_out_again.json()["authenticated"] is False


async def test_assistant_rejects_a_model_outside_the_server_allowlist(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    conversation = await create_conversation(client)

    rejected = await ask(
        client,
        conversation["id"],
        "What is tomorrow?",
        model="browser-invented-model",
    )

    assert rejected.status_code == 400
    assert rejected.json()["code"] == "invalid_ai_model"
    assert fake_codex.calls == []


async def test_read_only_question_reaches_mocked_codex_with_private_calendar_context(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    writable = await create_calendar(client, name="Personal")
    await create_event(client, writable["id"], **upcoming_event_times())
    protected = await create_calendar(client, name="Imported", is_read_only=True)
    conversation = await create_conversation(client)

    response = await ask(
        client,
        conversation["id"],
        "What do I have tomorrow?",
        model="gpt-5.6-terra",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "completed"
    assert body["job"]["model"] == "gpt-5.6-terra"
    assert body["assistant_message"]["role"] == "assistant"
    assert "planning session" in body["assistant_message"]["content"].lower()
    assert body["conversation"]["title"] == "What do I have tomorrow?"
    assert len(fake_codex.calls) == 1
    call = fake_codex.calls[0]
    assert call["model"] == "gpt-5.6-terra"
    assert {item["name"] for item in call["calendars"]} == {"Personal", "Imported"}
    imported_context = next(item for item in call["calendars"] if item["id"] == protected["id"])
    assert imported_context["is_read_only"] is True
    assert call["events"][0]["title"] == "Planning session"
    assert "subscription_url" not in json.dumps(call["calendars"])
    assert "Proposal behavior" in call["policy"]
    assert "proposal" in call["schema"]["properties"]
    assert "oneOf" not in json.dumps(call["schema"])
    assert_strict_object_schemas(call["schema"])
    assert not any(".env" in name for name in call["files"])
    assert not Path(call["root"]).exists()

    calendars_after = await client.get("/api/v1/calendars")
    events_after = await client.get("/api/v1/events")
    assert len(calendars_after.json()) == 2
    assert len(events_after.json()) == 1


async def test_conversation_history_is_stored_and_supplied_without_hidden_reasoning(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    conversation = await create_conversation(client)
    first = await ask(client, conversation["id"], "Which calendars are read-only?")
    assert first.status_code == 200
    fake_codex.response = json.dumps(
        {"message": "There are no calendars in the supplied context.", "proposal": None}
    )

    second = await ask(client, conversation["id"], "And what is on Saturday?")

    assert second.status_code == 200
    detail = await client.get(f"/api/v1/assistant/conversations/{conversation['id']}")
    assert [message["role"] for message in detail.json()["messages"]] == [
        "owner",
        "assistant",
        "owner",
        "assistant",
    ]
    request_data = fake_codex.calls[1]["request"]
    assert "Which calendars are read-only?" in request_data
    assert "You have a planning session" in request_data
    assert "hidden reasoning" not in detail.text.lower()


async def test_invalid_response_is_corrected_automatically_once(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    conversation = await create_conversation(client)
    fake_codex.responses = [
        '{"message":"I can help","proposal":null,"unexpected":true}',
        json.dumps(
            {
                "message": "I can help with general questions and your calendar.",
                "proposal": None,
                "additional_proposals": [],
                "citations": [],
            }
        ),
    ]

    response = await ask(client, conversation["id"], "What can you help me with?")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "completed"
    assert body["assistant_message"]["content"] == (
        "I can help with general questions and your calendar."
    )
    assert len(fake_codex.calls) == 2
    correction_request = fake_codex.calls[1]["request"]
    assert '"error_code": "invalid_assistant_response"' in correction_request
    assert '"validation_stage": "response_schema"' in correction_request


async def test_retry_receives_safe_validation_feedback_and_corrects_weekly_byday(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client, name="Gym")
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I can create the workout after confirmation.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Create a twice-weekly workout",
                "actions": [
                    {
                        "operation": "create_event",
                        "calendar_id": calendar["id"],
                        "event": {
                            "title": "Legs workout",
                            "description": "Push-Pull-Legs gym session",
                            "location": None,
                            "start_at": "2026-07-22T19:00:00+02:00",
                            "end_at": "2026-07-22T21:00:00+02:00",
                            "all_day": False,
                            "timezone": "Europe/Stockholm",
                            "recurrence_rule": "FREQ=WEEKLY;BYDAY=XX;COUNT=9",
                            "status": "confirmed",
                        },
                    }
                ],
            },
        }
    )

    failed = await ask(client, conversation["id"], "Create it on Wednesdays and Saturdays")

    assert failed.status_code == 200, failed.text
    assert failed.json()["proposal"] is None
    assert failed.json()["job"]["status"] == "failed"
    assert failed.json()["job"]["safe_error_code"] == "invalid_recurrence"

    fake_codex.response = json.dumps(
        {
            "message": "I corrected the recurrence rule and can create it after confirmation.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Create a twice-weekly workout",
                "actions": [
                    {
                        "operation": "create_event",
                        "calendar_id": calendar["id"],
                        "event": {
                            "title": "Legs workout",
                            "description": "Push-Pull-Legs gym session",
                            "location": None,
                            "start_at": "2026-07-22T19:00:00+02:00",
                            "end_at": "2026-07-22T21:00:00+02:00",
                            "all_day": False,
                            "timezone": "Europe/Stockholm",
                            "recurrence_rule": "FREQ=WEEKLY;BYDAY=WE,SA;COUNT=9",
                            "status": "confirmed",
                        },
                    }
                ],
            },
        }
    )
    retried = await client.post(
        f"/api/v1/assistant/jobs/{failed.json()['job']['id']}/retry"
    )

    assert retried.status_code == 200, retried.text
    assert retried.json()["job"]["status"] == "awaiting_confirmation"
    retry_request = fake_codex.calls[-1]["request"]
    assert '"recent_backend_feedback"' in retry_request
    assert '"error_code": "invalid_recurrence"' in retry_request
    assert "Weekly recurrence days must use unique" in retry_request

    confirmed = await client.post(
        f"/api/v1/assistant/proposals/{retried.json()['proposal']['id']}/confirm"
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "completed"
    events = (await client.get("/api/v1/events")).json()
    assert events[0]["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=WE,SA;COUNT=9"


async def test_proposal_output_is_rejected_and_failed_job_can_retry_safely(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client, name="Protected from Codex")
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I changed it.",
            "proposal": {
                "type": "calendar_change",
                "actions": [{"operation": "delete_calendar", "calendar_id": calendar["id"]}],
            },
        }
    )

    rejected = await ask(client, conversation["id"], "Delete my calendar")

    assert rejected.status_code == 200
    rejected_body = rejected.json()
    assert rejected_body["job"]["status"] == "failed"
    assert rejected_body["assistant_message"] is None
    assert rejected_body["job"]["safe_error"] == (
        "The assistant's reply did not match the required safe response format, so the "
        "backend rejected it before saving an answer or changing calendar data."
    )
    assert rejected_body["job"]["safe_error_details"]["failure_stage"] == "validating"
    assert rejected_body["job"]["safe_error_details"]["validation_stage"] == (
        "response_schema"
    )
    assert rejected_body["job"]["safe_error_details"]["validation_errors"]
    diagnostic_error_id = rejected_body["job"]["diagnostic_error_id"]
    assert uuid.UUID(diagnostic_error_id)
    diagnostic = await client.get(
        f"/api/v1/diagnostics/errors/{diagnostic_error_id}"
    )
    assert diagnostic.status_code == 200, diagnostic.text
    assert diagnostic.json()["operation"] == "assistant_job"
    assert diagnostic.json()["details"]["job_id"] == rejected_body["job"]["id"]
    assert diagnostic.json()["details"]["validation_errors"]
    assert len((await client.get("/api/v1/calendars")).json()) == 1

    fake_codex.response = json.dumps(
        {
            "message": "Calendar changes are unavailable in read-only mode.",
            "proposal": None,
        }
    )
    retried = await client.post(f"/api/v1/assistant/jobs/{rejected_body['job']['id']}/retry")

    assert retried.status_code == 200, retried.text
    assert retried.json()["job"]["status"] == "completed"
    assert retried.json()["job"]["safe_error_details"] == {}
    assert retried.json()["job"]["diagnostic_error_id"] is None
    detail = await client.get(f"/api/v1/assistant/conversations/{conversation['id']}")
    assert [message["role"] for message in detail.json()["messages"]] == [
        "owner",
        "assistant",
    ]
    assert len((await client.get("/api/v1/calendars")).json()) == 1


async def test_runtime_failure_preserves_owner_message_and_workspace_is_deleted(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    conversation = await create_conversation(client)
    fake_codex.fail_with = AssistantRuntimeError("Codex is unavailable for this test.")

    response = await ask(client, conversation["id"], "What is next?")

    assert response.status_code == 200
    body = response.json()
    assert body["job"]["status"] == "failed"
    assert body["job"]["safe_error"] == "Codex is unavailable for this test."
    assert body["assistant_message"] is None
    detail = await client.get(f"/api/v1/assistant/conversations/{conversation['id']}")
    assert [(item["role"], item["content"]) for item in detail.json()["messages"]] == [
        ("owner", "What is next?")
    ]
    assert not Path(fake_codex.calls[0]["root"]).exists()


async def test_owner_can_cancel_an_active_assistant_request(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    conversation = await create_conversation(client)
    fake_codex.started_event = asyncio.Event()
    fake_codex.release_event = asyncio.Event()
    request_task = asyncio.create_task(
        ask(client, conversation["id"], "Take your time explaining tomorrow.")
    )
    await asyncio.wait_for(fake_codex.started_event.wait(), timeout=2)

    cancelled = await client.post(
        f"/api/v1/assistant/conversations/{conversation['id']}/cancel"
    )

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["safe_error_code"] == "assistant_job_cancelled"
    turn = await asyncio.wait_for(request_task, timeout=2)
    assert turn.status_code == 200, turn.text
    assert turn.json()["job"]["status"] == "cancelled"
    assert turn.json()["assistant_message"] is None
    detail = await client.get(f"/api/v1/assistant/conversations/{conversation['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["jobs"][-1]["status"] == "cancelled"
    assert [item["role"] for item in detail.json()["messages"]] == ["owner"]
    assert not Path(fake_codex.calls[0]["root"]).exists()

    fake_codex.started_event = None
    fake_codex.release_event = None
    follow_up = await ask(client, conversation["id"], "What is two plus two?")
    assert follow_up.status_code == 200, follow_up.text
    assert follow_up.json()["job"]["status"] == "completed"
    assert "Take your time explaining tomorrow." not in fake_codex.calls[-1]["request"]


async def test_unknown_assistant_resources_return_clear_errors(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    conversation = await client.get(
        "/api/v1/assistant/conversations/00000000-0000-0000-0000-000000000001"
    )
    job = await client.get("/api/v1/assistant/jobs/00000000-0000-0000-0000-000000000002")
    assert conversation.status_code == 404
    assert conversation.json()["code"] == "assistant_conversation_not_found"
    assert job.status_code == 404
    assert job.json()["code"] == "assistant_job_not_found"


async def test_create_calendar_proposal_waits_for_confirmation_and_is_idempotent(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I can create a private calendar after you confirm.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Create the Private calendar",
                "actions": [
                    {
                        "operation": "create_calendar",
                        "name": "Private",
                        "description": "Personal appointments",
                        "color": "#29584c",
                    }
                ],
            },
        }
    )

    proposed = await ask(client, conversation["id"], "Create a private calendar")

    assert proposed.status_code == 200, proposed.text
    proposal = proposed.json()["proposal"]
    assert proposed.json()["job"]["status"] == "awaiting_confirmation"
    assert proposal["status"] == "awaiting_confirmation"
    assert proposal["affected_events"] == 0
    assert (await client.get("/api/v1/calendars")).json() == []

    first = await client.post(f"/api/v1/assistant/proposals/{proposal['id']}/confirm")
    second = await client.post(f"/api/v1/assistant/proposals/{proposal['id']}/confirm")

    assert first.status_code == 200, first.text
    assert first.json()["status"] == "completed"
    assert second.json()["status"] == "completed"
    calendars = (await client.get("/api/v1/calendars")).json()
    assert [calendar["name"] for calendar in calendars] == ["Private"]
    assert calendars[0]["source_type"] == "local"
    assert calendars[0]["is_read_only"] is False
    assert first.json()["action_records"][0]["executed_at"] is not None


async def test_linked_batches_prepare_and_confirm_thirty_events_independently(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client, name="Testing")
    conversation = await create_conversation(client)
    starts_at = datetime(2026, 7, 21, 10, 0, tzinfo=ZoneInfo("Europe/Stockholm"))

    def create_action(position: int) -> dict[str, Any]:
        start = starts_at + timedelta(days=position)
        return {
            "operation": "create_event",
            "calendar_id": calendar["id"],
            "event": {
                "title": f"Test event {position + 1}",
                "description": f"Linked batch event {position + 1} of 30",
                "location": None,
                "start_at": start.isoformat(),
                "end_at": (start + timedelta(hours=1)).isoformat(),
                "all_day": False,
                "timezone": "Europe/Stockholm",
                "recurrence_rule": None,
                "status": "confirmed",
            },
        }

    batches = [
        {
            "type": "calendar_change",
            "summary": f"Create test events {offset + 1}–{offset + 10}",
            "actions": [create_action(position) for position in range(offset, offset + 10)],
        }
        for offset in (0, 10, 20)
    ]
    fake_codex.response = json.dumps(
        {
            "message": "I prepared all 30 events as three separately confirmed batches.",
            "proposal": batches[0],
            "additional_proposals": batches[1:],
        }
    )

    proposed = await ask(client, conversation["id"], "Create 30 daily test events")

    assert proposed.status_code == 200, proposed.text
    body = proposed.json()
    assert body["job"]["status"] == "awaiting_confirmation"
    assert len(body["proposals"]) == 3
    assert body["proposal"]["id"] == body["proposals"][0]["id"]
    assert [item["batch_position"] for item in body["proposals"]] == [1, 2, 3]
    assert all(item["batch_count"] == 3 for item in body["proposals"])
    assert all(item["affected_events"] == 10 for item in body["proposals"])
    assert (await client.get("/api/v1/events")).json() == []

    first_id, second_id, third_id = [item["id"] for item in body["proposals"]]
    first = await client.post(f"/api/v1/assistant/proposals/{first_id}/confirm")
    duplicate = await client.post(f"/api/v1/assistant/proposals/{first_id}/confirm")
    assert first.json()["status"] == "completed"
    assert duplicate.json()["status"] == "completed"
    assert len((await client.get("/api/v1/events")).json()) == 10
    assert (await client.get(f"/api/v1/assistant/jobs/{body['job']['id']}")).json()[
        "status"
    ] == "awaiting_confirmation"

    await client.post(f"/api/v1/assistant/proposals/{second_id}/confirm")
    assert len((await client.get("/api/v1/events")).json()) == 20
    await client.post(f"/api/v1/assistant/proposals/{third_id}/confirm")
    events = (await client.get("/api/v1/events")).json()
    assert len(events) == 30
    assert {event["title"] for event in events} == {
        f"Test event {position}" for position in range(1, 31)
    }
    assert (await client.get(f"/api/v1/assistant/jobs/{body['job']['id']}")).json()[
        "status"
    ] == "completed"


async def test_linked_batches_reject_edits_and_large_recurring_batches(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client)
    event = await create_event(client, calendar["id"])
    conversation = await create_conversation(client)
    create_action = {
        "operation": "create_event",
        "calendar_id": calendar["id"],
        "event": {
            "title": "Safe create",
            "description": None,
            "location": None,
            "start_at": "2026-07-28T14:00:00+02:00",
            "end_at": "2026-07-28T15:00:00+02:00",
            "all_day": False,
            "timezone": "Europe/Stockholm",
            "recurrence_rule": None,
            "status": "confirmed",
        },
    }
    fake_codex.response = json.dumps(
        {
            "message": "Unsafe linked edit.",
            "proposal": {
                "type": "calendar_change",
                "summary": "First batch",
                "actions": [create_action],
            },
            "additional_proposals": [
                {
                    "type": "calendar_change",
                    "summary": "Unsafe edit batch",
                    "actions": [
                        {
                            "operation": "update_event",
                            "calendar_id": calendar["id"],
                            "event_id": event["id"],
                            "changes": {"title": "Changed"},
                            "recurrence_scope": None,
                            "occurrence_start_at": None,
                        }
                    ],
                }
            ],
        }
    )

    mixed = await ask(client, conversation["id"], "Create and edit in batches")
    assert mixed.json()["job"]["status"] == "failed"
    assert mixed.json()["proposals"] == []
    assert (await client.get(f"/api/v1/events/{event['id']}")).json()["title"] == (
        "Planning session"
    )

    second_conversation = await create_conversation(client)
    recurring_action = {
        **create_action,
        "event": {
            **create_action["event"],
            "title": "Too-large recurring series",
            "recurrence_rule": "FREQ=DAILY;COUNT=11",
        },
    }
    fake_codex.response = json.dumps(
        {
            "message": "Create eleven recurring events.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Create an eleven-event series",
                "actions": [recurring_action],
            },
            "additional_proposals": [],
        }
    )

    too_large = await ask(client, second_conversation["id"], "Create 11 daily events")
    assert too_large.json()["job"]["status"] == "failed"
    assert too_large.json()["job"]["safe_error_code"] == "assistant_proposal_limit"


async def test_update_calendar_and_create_event_proposals_execute_only_after_confirmation(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client, name="Personal")
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I can rename the calendar and add the appointment.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Rename Personal and create dentist appointment",
                "actions": [
                    {
                        "operation": "update_calendar",
                        "calendar_id": calendar["id"],
                        "changes": {
                            "name": "Private",
                            "description": None,
                            "color": "#335577",
                            "changed_fields": ["name", "color"],
                        },
                    },
                    {
                        "operation": "create_event",
                        "calendar_id": calendar["id"],
                        "event": {
                            "title": "Dentist",
                            "description": None,
                            "location": "Clinic",
                            "start_at": "2026-07-28T14:00:00+02:00",
                            "end_at": "2026-07-28T15:00:00+02:00",
                            "all_day": False,
                            "timezone": "Europe/Oslo",
                            "recurrence_rule": None,
                            "status": "confirmed",
                        },
                    },
                ],
            },
        }
    )

    proposed = await ask(client, conversation["id"], "Rename it and add my dentist")
    proposal = proposed.json()["proposal"]
    assert (await client.get(f"/api/v1/calendars/{calendar['id']}")).json()["name"] == ("Personal")
    assert (await client.get("/api/v1/events")).json() == []

    confirmed = await client.post(f"/api/v1/assistant/proposals/{proposal['id']}/confirm")

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "completed", confirmed.text
    updated = (await client.get(f"/api/v1/calendars/{calendar['id']}")).json()
    events = (await client.get("/api/v1/events")).json()
    assert (updated["name"], updated["color"]) == ("Private", "#335577")
    assert updated["description"] == "Ordinary local calendar"
    assert [(event["title"], event["location"]) for event in events] == [("Dentist", "Clinic")]


async def test_update_event_proposal_executes_after_confirmation(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client)
    event = await create_event(client, calendar["id"])
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I can move the planning session after confirmation.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Move the planning session",
                "actions": [
                    {
                        "operation": "update_event",
                        "calendar_id": calendar["id"],
                        "event_id": event["id"],
                        "changes": {
                            "calendar_id": None,
                            "title": None,
                            "description": None,
                            "location": None,
                            "start_at": "2026-07-20T12:00:00+02:00",
                            "end_at": "2026-07-20T13:00:00+02:00",
                            "all_day": None,
                            "timezone": None,
                            "recurrence_rule": None,
                            "status": None,
                            "changed_fields": ["start_at", "end_at"],
                        },
                        "recurrence_scope": None,
                        "occurrence_start_at": None,
                    }
                ],
            },
        }
    )

    proposed = await ask(client, conversation["id"], "Move my planning session")
    before = (await client.get(f"/api/v1/events/{event['id']}")).json()
    assert before["start_at"] == "2026-07-20T08:00:00Z"

    confirmed = await client.post(
        f"/api/v1/assistant/proposals/{proposed.json()['proposal']['id']}/confirm"
    )

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "completed"
    updated = (await client.get(f"/api/v1/events/{event['id']}")).json()
    assert updated["start_at"] == "2026-07-20T10:00:00Z"
    assert updated["end_at"] == "2026-07-20T11:00:00Z"


async def test_update_event_revalidates_snapshot_and_fails_if_event_changed(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client)
    event = await create_event(client, calendar["id"])
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I can move the planning session after confirmation.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Move the planning session",
                "actions": [
                    {
                        "operation": "update_event",
                        "calendar_id": calendar["id"],
                        "event_id": event["id"],
                        "changes": {
                            "start_at": "2026-07-20T12:00:00+02:00",
                            "end_at": "2026-07-20T13:00:00+02:00",
                        },
                        "recurrence_scope": None,
                        "occurrence_start_at": None,
                    }
                ],
            },
        }
    )
    proposed = await ask(client, conversation["id"], "Move my planning session")
    proposal = proposed.json()["proposal"]
    manually_changed = await client.patch(
        f"/api/v1/events/{event['id']}", json={"title": "Owner changed this"}
    )
    assert manually_changed.status_code == 200

    confirmed = await client.post(f"/api/v1/assistant/proposals/{proposal['id']}/confirm")

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "failed"
    assert confirmed.json()["result"]["error_code"] == "assistant_proposal_state_conflict"
    assert "changed before confirmation" in confirmed.json()["safe_error"]
    unchanged_time = (await client.get(f"/api/v1/events/{event['id']}")).json()
    assert unchanged_time["start_at"] == "2026-07-20T08:00:00Z"
    assert unchanged_time["title"] == "Owner changed this"

    fake_codex.response = json.dumps(
        {
            "message": (
                "I can see the backend rejected the stale proposal and will use "
                "the current event."
            ),
            "proposal": None,
        }
    )
    follow_up = await ask(client, conversation["id"], "Please correct it and try again")

    assert follow_up.status_code == 200, follow_up.text
    follow_up_request = fake_codex.calls[-1]["request"]
    assert '"source": "calendar_proposal"' in follow_up_request
    assert '"error_code": "assistant_proposal_state_conflict"' in follow_up_request
    assert "changed before confirmation" in follow_up_request
    assert '"attempted_actions"' in follow_up_request


async def test_confirmation_rechecks_read_only_calendar_protection(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client)
    event = await create_event(client, calendar["id"])
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I can rename it after confirmation.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Rename the event",
                "actions": [
                    {
                        "operation": "update_event",
                        "calendar_id": calendar["id"],
                        "event_id": event["id"],
                        "changes": {"title": "Renamed by assistant"},
                        "recurrence_scope": None,
                        "occurrence_start_at": None,
                    }
                ],
            },
        }
    )
    proposed = await ask(client, conversation["id"], "Rename it")
    protected = await client.patch(
        f"/api/v1/calendars/{calendar['id']}", json={"is_read_only": True}
    )
    assert protected.status_code == 200

    confirmed = await client.post(
        f"/api/v1/assistant/proposals/{proposed.json()['proposal']['id']}/confirm"
    )

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "failed"
    assert confirmed.json()["confirmed_at"] is not None
    assert confirmed.json()["action_records"][0]["confirmed_at"] is not None
    unchanged = (await client.get(f"/api/v1/events/{event['id']}")).json()
    assert unchanged["title"] == "Planning session"


async def test_recurring_event_proposal_requires_an_explicit_scope(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client)
    event = await create_event(client, calendar["id"], recurrence_rule="FREQ=WEEKLY;COUNT=4")
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I can rename the recurring event.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Ambiguous recurring change",
                "actions": [
                    {
                        "operation": "update_event",
                        "calendar_id": calendar["id"],
                        "event_id": event["id"],
                        "changes": {"title": "Recurring planning"},
                        "recurrence_scope": None,
                        "occurrence_start_at": None,
                    }
                ],
            },
        }
    )

    response = await ask(client, conversation["id"], "Rename my recurring event")

    assert response.status_code == 200
    assert response.json()["job"]["status"] == "failed"
    assert response.json()["proposal"] is None
    unchanged = (await client.get(f"/api/v1/events/{event['id']}")).json()
    assert unchanged["title"] == "Planning session"


async def test_delete_one_event_can_be_rejected_or_confirmed(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client)
    first_event = await create_event(client, calendar["id"])
    conversation = await create_conversation(client)

    def delete_response(event_id: str) -> str:
        return json.dumps(
            {
                "message": "I found one matching event. Confirm if it should be deleted.",
                "proposal": {
                    "type": "calendar_change",
                    "summary": "Delete one planning session",
                    "actions": [
                        {
                            "operation": "delete_event",
                            "calendar_id": calendar["id"],
                            "event_id": event_id,
                            "recurrence_scope": None,
                            "occurrence_start_at": None,
                        }
                    ],
                },
            }
        )

    fake_codex.response = delete_response(first_event["id"])
    first = await ask(client, conversation["id"], "Delete the planning session")
    rejected = await client.post(
        f"/api/v1/assistant/proposals/{first.json()['proposal']['id']}/reject"
    )
    assert rejected.json()["status"] == "rejected"
    assert (await client.get(f"/api/v1/events/{first_event['id']}")).status_code == 200

    second_event = await create_event(
        client,
        calendar["id"],
        title="Second planning session",
        start_at="2026-07-21T10:00:00+02:00",
        end_at="2026-07-21T11:00:00+02:00",
    )
    fake_codex.response = delete_response(second_event["id"])
    second = await ask(client, conversation["id"], "Delete the second session")
    confirmed = await client.post(
        f"/api/v1/assistant/proposals/{second.json()['proposal']['id']}/confirm"
    )
    assert confirmed.json()["status"] == "completed"
    assert (await client.get(f"/api/v1/events/{second_event['id']}")).status_code == 404
    assert (await client.get(f"/api/v1/events/{first_event['id']}")).status_code == 200


@pytest.mark.parametrize("invalid_target", ["read_only", "missing"])
async def test_proposals_reject_read_only_or_unknown_calendar_targets(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
    invalid_target: str,
) -> None:
    calendar_id = "00000000-0000-0000-0000-000000000099"
    if invalid_target == "read_only":
        calendar_id = (await create_calendar(client, is_read_only=True))["id"]
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I can create it.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Unsafe create event target",
                "actions": [
                    {
                        "operation": "create_event",
                        "calendar_id": calendar_id,
                        "event": {
                            "title": "Unsafe",
                            "description": None,
                            "location": None,
                            "start_at": "2026-07-28T14:00:00+02:00",
                            "end_at": "2026-07-28T15:00:00+02:00",
                            "all_day": False,
                            "timezone": "Europe/Oslo",
                            "recurrence_rule": None,
                            "status": "confirmed",
                        },
                    }
                ],
            },
        }
    )

    response = await ask(client, conversation["id"], "Create an unsafe event")

    assert response.status_code == 200
    assert response.json()["job"]["status"] == "failed"
    assert response.json()["proposal"] is None
    assert (await client.get("/api/v1/events")).json() == []


async def test_bulk_delete_and_unknown_operations_are_rejected(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    calendar = await create_calendar(client)
    events = [
        await create_event(client, calendar["id"]),
        await create_event(
            client,
            calendar["id"],
            title="Second",
            start_at="2026-07-21T10:00:00+02:00",
            end_at="2026-07-21T11:00:00+02:00",
        ),
    ]
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "Delete both.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Bulk delete",
                "actions": [
                    {
                        "operation": "delete_event",
                        "calendar_id": calendar["id"],
                        "event_id": event["id"],
                        "recurrence_scope": None,
                        "occurrence_start_at": None,
                    }
                    for event in events
                ],
            },
        }
    )
    bulk = await ask(client, conversation["id"], "Delete both")
    assert bulk.json()["job"]["status"] == "failed"

    fake_codex.response = json.dumps(
        {
            "message": "Delete the calendar.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Unknown operation",
                "actions": [{"operation": "delete_calendar", "calendar_id": calendar["id"]}],
            },
        }
    )
    unknown = await ask(client, conversation["id"], "Delete my calendar")
    assert unknown.json()["job"]["status"] == "failed"
    assert len((await client.get("/api/v1/events")).json()) == 2


async def test_expired_proposal_cannot_execute(
    client: AsyncClient,
    session: AsyncSession,
    fake_codex: FakeCodexAdapter,
) -> None:
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "I can create it after confirmation.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Create expired calendar",
                "actions": [
                    {
                        "operation": "create_calendar",
                        "name": "Expired",
                        "description": None,
                        "color": "#29584c",
                    }
                ],
            },
        }
    )
    proposed = await ask(client, conversation["id"], "Create expired")
    proposal_id = proposed.json()["proposal"]["id"]
    proposal = await session.get(AssistantProposal, uuid.UUID(proposal_id))
    assert proposal is not None
    proposal.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.commit()

    confirmed = await client.post(f"/api/v1/assistant/proposals/{proposal_id}/confirm")

    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "expired"
    assert (await client.get("/api/v1/calendars")).json() == []


async def test_assistant_audit_lists_recent_proposal_lifecycle_records(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    conversation = await create_conversation(client)

    def create_response(name: str) -> str:
        return json.dumps(
            {
                "message": f"I can create {name} after confirmation.",
                "proposal": {
                    "type": "calendar_change",
                    "summary": f"Create {name}",
                    "actions": [
                        {
                            "operation": "create_calendar",
                            "name": name,
                            "description": None,
                            "color": "#29584c",
                        }
                    ],
                },
            }
        )

    fake_codex.response = create_response("Rejected calendar")
    rejected_turn = await ask(client, conversation["id"], "Create one")
    rejected_id = rejected_turn.json()["proposal"]["id"]
    await client.post(f"/api/v1/assistant/proposals/{rejected_id}/reject")

    fake_codex.response = create_response("Confirmed calendar")
    completed_turn = await ask(client, conversation["id"], "Create another")
    completed_id = completed_turn.json()["proposal"]["id"]
    await client.post(f"/api/v1/assistant/proposals/{completed_id}/confirm")

    recent = await client.get("/api/v1/assistant/audit?limit=1")
    complete = await client.get("/api/v1/assistant/audit?limit=2")

    assert recent.status_code == 200
    assert [item["id"] for item in recent.json()] == [completed_id]
    assert recent.json()[0]["status"] == "completed"
    assert recent.json()[0]["action_records"][0]["confirmed_at"] is not None
    assert recent.json()[0]["action_records"][0]["executed_at"] is not None
    assert [item["status"] for item in complete.json()] == [
        "completed",
        "rejected",
    ]


async def test_invalid_model_content_is_not_written_to_application_logs(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_marker = "PRIVATE-CALENDAR-CONTENT-MUST-NOT-BE-LOGGED"
    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": private_marker,
            "proposal": {
                "type": "calendar_change",
                "summary": "Unsafe",
                "actions": [{"operation": "delete_calendar"}],
            },
        }
    )

    with caplog.at_level("WARNING"):
        response = await ask(client, conversation["id"], "Do something unsafe")

    assert response.status_code == 200
    assert response.json()["job"]["status"] == "failed"
    assert private_marker not in caplog.text
    assert "invalid_assistant_response" in caplog.text
    diagnostic_error_id = response.json()["job"]["diagnostic_error_id"]
    diagnostic = await client.get(
        f"/api/v1/diagnostics/errors/{diagnostic_error_id}"
    )
    assert private_marker not in diagnostic.text


async def test_course_note_capability_question_is_general_help_without_private_context(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    await create_course_note_context(
        client,
        course_name="Datasekretess",
        course_code="DATSEC",
        note_title="Privacy principles",
        note_body="Purpose limitation constrains later data use.",
    )
    await create_course_note_context(
        client,
        course_name="Operating Systems",
        course_code="OS101",
        note_title="Scheduling notes",
        note_body="The scheduler allocates CPU time.",
    )
    fake_codex.response = json.dumps(
        {
            "message": (
                "I can explain and compare relevant notes with citations, create study aids, "
                "and provide general help or code snippets in chat."
            ),
            "proposal": None,
            "additional_proposals": [],
            "citations": [],
        }
    )
    conversation = await create_conversation(client)

    response = await ask(
        client,
        conversation["id"],
        "What can you do with course notes?",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "completed"
    assert body["assistant_message"]["citations"] == []
    call = fake_codex.calls[-1]
    assert call["courses"] == []
    assert call["notes"] == []
    assert call["selected_slide_text"] == []
    assert "COURSES.json" not in call["files"]
    assert "NOTES.json" not in call["files"]
    assert "private general-purpose assistant" in call["policy"]
    assert "provide code snippets directly in the chat response" in call["policy"]


async def test_calendar_only_request_ignores_false_note_matches_and_receives_all_calendars(
    client: AsyncClient,
    session: AsyncSession,
    fake_codex: FakeCodexAdapter,
) -> None:
    course, note, _ = await create_course_note_context(
        client,
        course_name="test",
        course_code="TEST",
        note_title="Testing notes written",
        note_body=(
            "I was not sure, but I can get something ready for a work out. "
            "PRIVATE-UNRELATED-NOTE"
        ),
    )
    linked_read_only = await create_calendar(
        client,
        name="Imported course timetable",
        is_read_only=True,
    )
    gym = await create_calendar(
        client,
        name="Gym",
        description="Push-Pull-Legs workout schedule",
        is_visible=False,
    )
    personal = await create_calendar(client, name="My Calendar")
    linked = await client.post(
        f"/api/v1/courses/{course['id']}/calendars",
        json={"calendar_id": linked_read_only["id"]},
    )
    assert linked.status_code == 201, linked.text

    fake_codex.response = json.dumps(
        {
            "message": "I can add the workout to Gym after confirmation.",
            "proposal": {
                "type": "calendar_change",
                "summary": "Add a one-hour workout to Gym",
                "actions": [
                    {
                        "operation": "create_event",
                        "calendar_id": gym["id"],
                        "event": {
                            "title": "Workout",
                            "description": None,
                            "location": None,
                            "start_at": "2026-08-01T10:00:00+02:00",
                            "end_at": "2026-08-01T11:00:00+02:00",
                            "all_day": False,
                            "timezone": "Europe/Oslo",
                            "recurrence_rule": None,
                            "status": "confirmed",
                        },
                    }
                ],
            },
            "additional_proposals": [],
            "citations": [],
        }
    )
    conversation = await create_conversation(client)

    response = await ask(
        client,
        conversation["id"],
        (
            "it is not but okey you get the benefit of the doubt add something to the "
            "Gym calender a work out that last 1hr that start at 10 am tomorrow"
        ),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "awaiting_confirmation"
    assert body["proposal"]["actions"][0]["calendar_id"] == gym["id"]
    call = fake_codex.calls[-1]
    assert call["courses"] == []
    assert call["notes"] == []
    assert call["selected_slide_text"] == []
    assert {item["id"] for item in call["calendars"]} == {
        linked_read_only["id"],
        gym["id"],
        personal["id"],
    }
    gym_context = next(item for item in call["calendars"] if item["id"] == gym["id"])
    assert gym_context["is_visible"] is False
    assert gym_context["is_read_only"] is False
    assert "COURSES.json" not in call["files"]
    assert "NOTES.json" not in call["files"]
    serialized_call = json.dumps(call, default=str)
    assert note["id"] not in serialized_call
    assert "PRIVATE-UNRELATED-NOTE" not in serialized_call

    audit = await session.scalar(
        select(AssistantContextAudit).where(
            AssistantContextAudit.job_id == uuid.UUID(body["job"]["id"])
        )
    )
    assert audit is not None
    assert audit.course_ids == []
    assert audit.note_ids == []
    assert audit.requires_clarification is False


@pytest.mark.parametrize(
    "question",
    [
        "Explain normalization in Datasekretess in plain language.",
        "Write me an email about normalization.",
    ],
)
async def test_general_questions_do_not_activate_matching_private_notes(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
    question: str,
) -> None:
    course, note, _ = await create_course_note_context(
        client,
        course_name="Datasekretess",
        course_code="DATSEC",
        note_title="Normalization",
        note_body="PRIVATE-NORMALIZATION-NOTE explains third normal form.",
    )
    fake_codex.response = json.dumps(
        {
            "message": "Here is a general-knowledge answer.",
            "proposal": None,
            "additional_proposals": [],
            "citations": [],
        }
    )
    conversation = await create_conversation(client)

    response = await ask(client, conversation["id"], question)

    assert response.status_code == 200, response.text
    assert response.json()["job"]["status"] == "completed"
    call = fake_codex.calls[-1]
    assert call["courses"] == []
    assert call["notes"] == []
    assert call["selected_slide_text"] == []
    assert "COURSES.json" not in call["files"]
    assert "NOTES.json" not in call["files"]
    serialized_call = json.dumps(call, default=str)
    assert course["id"] not in serialized_call
    assert note["id"] not in serialized_call
    assert "PRIVATE-NORMALIZATION-NOTE" not in serialized_call


async def test_course_question_uses_only_relevant_notes_slides_and_linked_calendar(
    client: AsyncClient,
    session: AsyncSession,
    fake_codex: FakeCodexAdapter,
) -> None:
    course, note, source = await create_course_note_context(
        client,
        course_name="Datasekretess",
        course_code="DATSEC",
        note_title="Normalization and disclosure",
        note_body=(
            "Normalization reduces duplicate personal data. "
            "API_KEY=sk-relevant-note-secret"
        ),
        slide_text=(
            "Third normal form reduces update anomalies. "
            "Bearer relevant-slide-token"
        ),
    )
    assert source is not None
    unrelated_course, unrelated_note, _ = await create_course_note_context(
        client,
        course_name="Operating Systems",
        course_code="OS101",
        note_title="Normalization elsewhere",
        note_body="OWNER_API_TOKEN=sk-unrelated-private-value",
    )
    relevant_calendar = await create_calendar(client, name="Datasekretess schedule")
    unrelated_calendar = await create_calendar(client, name="Private errands")
    linked = await client.post(
        f"/api/v1/courses/{course['id']}/calendars",
        json={"calendar_id": relevant_calendar["id"]},
    )
    assert linked.status_code == 201
    await create_event(
        client,
        relevant_calendar["id"],
        title="Privacy lecture",
        description="TOKEN=sk-relevant-calendar-secret",
        **upcoming_event_times(),
    )
    await create_event(
        client,
        unrelated_calendar["id"],
        title="Private appointment",
        **upcoming_event_times(),
    )

    conversation = await create_conversation(client)
    fake_codex.response = json.dumps(
        {
            "message": "PRIOR-OPERATING-SYSTEMS-ANSWER",
            "proposal": None,
            "additional_proposals": [],
            "citations": [
                {
                    "course_id": unrelated_course["id"],
                    "course_name": unrelated_course["name"],
                    "note_id": unrelated_note["id"],
                    "note_title": unrelated_note["title"],
                    "source_id": None,
                    "source_name": None,
                    "slide_number": None,
                }
            ],
        }
    )
    prior = await ask(
        client,
        conversation["id"],
        "Summarize the Operating Systems note about normalization.",
    )
    assert prior.status_code == 200, prior.text
    assert prior.json()["job"]["status"] == "completed"

    fake_codex.response = json.dumps(
        {
            "message": (
                "Your note says normalization reduces duplicate personal data, "
                "and the linked deck connects third normal form to update anomalies."
            ),
            "proposal": None,
            "additional_proposals": [],
            "citations": [
                {
                    "course_id": course["id"],
                    "course_name": course["name"],
                    "note_id": note["id"],
                    "note_title": note["title"],
                    "source_id": source["id"],
                    "source_name": source["display_name"],
                    "slide_number": 1,
                }
            ],
        }
    )
    response = await ask(
        client,
        conversation["id"],
        (
            "What did I write about normalization in Datasekretess? "
            "token=sk-relevant-question-secret"
        ),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "completed"
    assert body["assistant_message"]["citations"][0]["note_id"] == note["id"]
    call = fake_codex.calls[-1]
    assert [item["id"] for item in call["courses"]] == [course["id"]]
    assert [item["id"] for item in call["notes"]] == [note["id"]]
    assert call["selected_slide_text"] == [
        {
            "note_id": note["id"],
            "source_id": source["id"],
            "source_name": source["display_name"],
            "slide_number": 1,
            "text": "Third normal form reduces update anomalies. [REDACTED]",
        }
    ]
    assert [item["id"] for item in call["calendars"]] == [relevant_calendar["id"]]
    assert [item["title"] for item in call["events"]] == ["Privacy lecture"]
    supplied_context = json.dumps(
        {
            key: call[key]
            for key in (
                "request",
                "calendars",
                "events",
                "courses",
                "notes",
                "slide_references",
                "selected_slide_text",
            )
        }
    )
    assert unrelated_course["id"] not in supplied_context
    assert "sk-unrelated-private-value" not in supplied_context
    assert "sk-relevant-note-secret" not in supplied_context
    assert "relevant-slide-token" not in supplied_context
    assert "sk-relevant-calendar-secret" not in supplied_context
    assert "sk-relevant-question-secret" not in supplied_context
    assert "[REDACTED]" in supplied_context
    assert "PRIOR-OPERATING-SYSTEMS-ANSWER" not in supplied_context
    assert "Private appointment" not in supplied_context
    assert "COURSES.json" in call["files"]
    assert "SELECTED_SLIDE_TEXT.json" in call["files"]

    fake_codex.response = json.dumps(
        {
            "message": "The linked course calendar contains the privacy lecture.",
            "proposal": None,
            "additional_proposals": [],
            "citations": [],
        }
    )
    calendar_question = await ask(
        client,
        conversation["id"],
        "What is on the Datasekretess calendar?",
    )
    assert calendar_question.status_code == 200, calendar_question.text
    calendar_call = fake_codex.calls[-1]
    assert calendar_call["notes"] == []
    assert calendar_call["selected_slide_text"] == []
    assert [item["id"] for item in calendar_call["calendars"]] == [
        relevant_calendar["id"]
    ]
    assert "Your note says normalization" not in calendar_call["request"]

    audit = await session.scalar(
        select(AssistantContextAudit).where(
            AssistantContextAudit.job_id == uuid.UUID(body["job"]["id"])
        )
    )
    assert audit is not None
    assert audit.course_ids == [course["id"]]
    assert audit.note_ids == [note["id"]]
    assert audit.source_ids == [source["id"]]
    assert audit.requires_clarification is False


async def test_course_question_asks_for_clarification_before_runtime(
    client: AsyncClient,
    session: AsyncSession,
    fake_codex: FakeCodexAdapter,
) -> None:
    first_course, _, _ = await create_course_note_context(
        client,
        course_name="Datasekretess",
        course_code="DATSEC",
        note_title="Database design",
        note_body="Normalization avoids update anomalies.",
    )
    second_course, _, _ = await create_course_note_context(
        client,
        course_name="Data Engineering",
        course_code="DE201",
        note_title="Warehouse design",
        note_body="Normalization can reduce duplication.",
    )
    conversation = await create_conversation(client)

    response = await ask(
        client,
        conversation["id"],
        "What did I write about normalization?",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "completed"
    assert "Which course do you mean?" in body["assistant_message"]["content"]
    assert first_course["name"] in body["assistant_message"]["content"]
    assert second_course["name"] in body["assistant_message"]["content"]
    assert body["assistant_message"]["citations"] == []
    assert fake_codex.calls == []
    audit = await session.scalar(
        select(AssistantContextAudit).where(
            AssistantContextAudit.job_id == uuid.UUID(body["job"]["id"])
        )
    )
    assert audit is not None
    assert set(audit.course_ids) == {first_course["id"], second_course["id"]}
    assert audit.note_ids == []
    assert audit.requires_clarification is True


async def test_invented_course_citation_fails_without_saving_answer(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    course, note, _ = await create_course_note_context(
        client,
        course_name="Datasekretess",
        course_code="DATSEC",
        note_title="Privacy principles",
        note_body="Data minimization limits unnecessary collection.",
    )
    fake_codex.response = json.dumps(
        {
            "message": "A claim with an invented citation.",
            "proposal": None,
            "additional_proposals": [],
            "citations": [
                {
                    "course_id": course["id"],
                    "course_name": course["name"],
                    "note_id": str(uuid.uuid4()),
                    "note_title": note["title"],
                    "source_id": None,
                    "source_name": None,
                    "slide_number": None,
                }
            ],
        }
    )
    conversation = await create_conversation(client)

    response = await ask(
        client,
        conversation["id"],
        "Summarize my latest notes from Datasekretess.",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "failed"
    assert body["job"]["safe_error_code"] == "invalid_assistant_response"
    assert body["job"]["safe_error_details"]["reason"] == (
        "A citation did not match the course and note context supplied to the model."
    )
    assert body["job"]["safe_error_details"]["validation_errors"] == [
        {
            "field": "citations.0",
            "message": "Course or note identity does not match supplied context.",
            "type": "citation_context_mismatch",
        }
    ]
    assert uuid.UUID(body["job"]["diagnostic_error_id"])
    assert body["assistant_message"] is None
    assert body["proposals"] == []


async def test_course_note_answer_requires_at_least_one_valid_citation(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    await create_course_note_context(
        client,
        course_name="Datasekretess",
        course_code="DATSEC",
        note_title="Privacy principles",
        note_body="Purpose limitation constrains later data use.",
    )
    fake_codex.response = json.dumps(
        {
            "message": "An uncited course-note answer.",
            "proposal": None,
            "additional_proposals": [],
            "citations": [],
        }
    )
    conversation = await create_conversation(client)

    response = await ask(
        client,
        conversation["id"],
        "Summarize my latest notes from Datasekretess.",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "failed"
    assert body["job"]["safe_error_code"] == "invalid_assistant_response"
    assert body["job"]["safe_error_details"]["validation_stage"] == (
        "citation_validation"
    )
    assert body["job"]["safe_error_details"]["validation_errors"] == [
        {
            "field": "citations",
            "message": "At least one supplied course-note citation is required.",
            "type": "citation_missing",
        }
    ]
    assert body["assistant_message"] is None
