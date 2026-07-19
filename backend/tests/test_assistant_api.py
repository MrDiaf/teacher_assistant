import json
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import AssistantProposal
from app.codex_runtime.adapter import (
    CodexAccountStatus,
    CodexDeviceLoginAttempt,
    CodexRuntimeResult,
    get_codex_adapter,
    get_codex_auth_manager,
)
from app.core.errors import AssistantRuntimeError
from app.main import app
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

    async def answer(self, workspace) -> CodexRuntimeResult:
        snapshot = {
            "root": workspace.root,
            "job_directory": workspace.job_directory,
            "policy": (workspace.job_directory / "AGENT.md").read_text(),
            "request": (workspace.job_directory / "REQUEST.md").read_text(),
            "calendars": json.loads((workspace.job_directory / "CALENDARS.json").read_text()),
            "events": json.loads((workspace.job_directory / "EVENTS.json").read_text()),
            "schema": json.loads((workspace.job_directory / "OUTPUT_SCHEMA.json").read_text()),
            "files": sorted(
                str(path.relative_to(workspace.job_directory))
                for path in workspace.job_directory.rglob("*")
            ),
        }
        self.calls.append(snapshot)
        if self.fail_with is not None:
            raise self.fail_with
        return CodexRuntimeResult(final_response=self.response)


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
def fake_codex() -> Iterator[FakeCodexAdapter]:
    adapter = FakeCodexAdapter()
    app.dependency_overrides[get_codex_adapter] = lambda: adapter
    try:
        yield adapter
    finally:
        app.dependency_overrides.pop(get_codex_adapter, None)


@pytest.fixture
def fake_codex_auth() -> Iterator[FakeCodexAuth]:
    auth = FakeCodexAuth()
    app.dependency_overrides[get_codex_auth_manager] = lambda: auth
    try:
        yield auth
    finally:
        app.dependency_overrides.pop(get_codex_auth_manager, None)


async def create_conversation(client: AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/assistant/conversations",
        json={"title": "Calendar conversation"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def ask(client: AsyncClient, conversation_id: str, content: str):
    return await client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/messages",
        json={"content": content},
    )


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
    signed_out = await client.get("/api/v1/assistant/auth")
    started = await client.post("/api/v1/assistant/auth/device-code")
    completed = await client.get(
        f"/api/v1/assistant/auth/device-code/{fake_codex_auth.attempt.login_id}"
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

    signed_out_again = await client.delete("/api/v1/assistant/auth")
    assert signed_out_again.json()["authenticated"] is False


async def test_read_only_question_reaches_mocked_codex_with_private_calendar_context(
    client: AsyncClient,
    fake_codex: FakeCodexAdapter,
) -> None:
    writable = await create_calendar(client, name="Personal")
    await create_event(client, writable["id"])
    protected = await create_calendar(client, name="Imported", is_read_only=True)
    conversation = await create_conversation(client)

    response = await ask(client, conversation["id"], "What do I have tomorrow?")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job"]["status"] == "completed"
    assert body["assistant_message"]["role"] == "assistant"
    assert "planning session" in body["assistant_message"]["content"].lower()
    assert body["conversation"]["title"] == "What do I have tomorrow?"
    assert len(fake_codex.calls) == 1
    call = fake_codex.calls[0]
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
        "The assistant returned an invalid response. No calendar data changed."
    )
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

    first = await client.post(
        f"/api/v1/assistant/proposals/{proposal['id']}/confirm"
    )
    second = await client.post(
        f"/api/v1/assistant/proposals/{proposal['id']}/confirm"
    )

    assert first.status_code == 200, first.text
    assert first.json()["status"] == "completed"
    assert second.json()["status"] == "completed"
    calendars = (await client.get("/api/v1/calendars")).json()
    assert [calendar["name"] for calendar in calendars] == ["Private"]
    assert calendars[0]["source_type"] == "local"
    assert calendars[0]["is_read_only"] is False
    assert first.json()["action_records"][0]["executed_at"] is not None


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
    assert (await client.get(f"/api/v1/calendars/{calendar['id']}")).json()["name"] == (
        "Personal"
    )
    assert (await client.get("/api/v1/events")).json() == []

    confirmed = await client.post(
        f"/api/v1/assistant/proposals/{proposal['id']}/confirm"
    )

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "completed", confirmed.text
    updated = (await client.get(f"/api/v1/calendars/{calendar['id']}")).json()
    events = (await client.get("/api/v1/events")).json()
    assert (updated["name"], updated["color"]) == ("Private", "#335577")
    assert updated["description"] == "Ordinary local calendar"
    assert [(event["title"], event["location"]) for event in events] == [
        ("Dentist", "Clinic")
    ]


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

    confirmed = await client.post(
        f"/api/v1/assistant/proposals/{proposal['id']}/confirm"
    )

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "failed"
    assert "changed before confirmation" in confirmed.json()["safe_error"]
    unchanged_time = (await client.get(f"/api/v1/events/{event['id']}")).json()
    assert unchanged_time["start_at"] == "2026-07-20T08:00:00Z"
    assert unchanged_time["title"] == "Owner changed this"


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
                "actions": [
                    {"operation": "delete_calendar", "calendar_id": calendar["id"]}
                ],
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

    confirmed = await client.post(
        f"/api/v1/assistant/proposals/{proposal_id}/confirm"
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "expired"
    assert (await client.get("/api/v1/calendars")).json() == []
