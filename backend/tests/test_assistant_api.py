import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

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
    assert "Current read-only phase" in call["policy"]
    assert "proposal" in call["schema"]["properties"]
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
