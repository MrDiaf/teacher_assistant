import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.codex_runtime.adapter import (
    CodexAuthManager,
    CodexRuntimeResult,
    CodexSdkAdapter,
    _used_runtime_tool,
)
from app.codex_runtime.parser import READ_ONLY_OUTPUT_SCHEMA, parse_read_only_answer
from app.codex_runtime.workspace import create_runtime_workspace
from app.core.config import Settings
from app.core.errors import InvalidAssistantResponseError


async def test_sdk_adapter_uses_read_only_sandbox_and_scrubbed_environment(
    monkeypatch,
    tmp_path,
) -> None:
    captured = {}

    class FakeThread:
        async def run(self, prompt, **options):
            captured["prompt"] = prompt
            captured["run_options"] = options
            return CodexRuntimeResult(
                final_response=json.dumps({"message": "Safe answer", "proposal": None})
            )

    class FakeAsyncCodex:
        def __init__(self, config):
            captured["config"] = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def thread_start(self, **options):
            captured["thread_options"] = options
            return FakeThread()

    monkeypatch.setattr("app.codex_runtime.adapter.AsyncCodex", FakeAsyncCodex)
    settings = Settings(
        database_url="postgresql+asyncpg://private:secret@database/app",
        openai_api_key="test-api-key",
        codex_auth_home=tmp_path / "codex-auth",
        codex_timeout_seconds=10,
    )
    adapter = CodexSdkAdapter(settings)

    with create_runtime_workspace(
        request_markdown="# Request",
        calendars=[],
        events=[],
        output_schema=READ_ONLY_OUTPUT_SCHEMA,
    ) as workspace:
        root = workspace.root
        result = await adapter.answer(workspace)
        assert result.final_response is not None
        assert captured["config"].env == {
            "PATH": captured["config"].env["PATH"],
            "LANG": "C.UTF-8",
            "HOME": str(workspace.runtime_home),
            "CODEX_HOME": str(tmp_path / "codex-auth"),
            "TMPDIR": str(workspace.temp_directory),
            "OPENAI_API_KEY": "test-api-key",
        }
        assert "DATABASE_URL" not in captured["config"].env
        assert "database" not in json.dumps(captured["config"].env).lower()
        assert 'shell_environment_policy.inherit="none"' in (captured["config"].config_overrides)
        assert "features.shell_tool=false" in captured["config"].config_overrides
        assert "features.unified_exec=false" in captured["config"].config_overrides
        assert "features.apps=false" in captured["config"].config_overrides
        assert "features.remote_plugin=false" in captured["config"].config_overrides
        assert "features.multi_agent=false" in captured["config"].config_overrides
        from openai_codex import ApprovalMode

        assert captured["thread_options"]["approval_mode"] == ApprovalMode.deny_all
        runtime_config = captured["thread_options"]["config"]
        assert runtime_config["default_permissions"] == "calendar-runtime-read-only"
        filesystem = runtime_config["permissions"]["calendar-runtime-read-only"]["filesystem"]
        assert filesystem[":workspace_roots"] == {".": "read"}
        assert filesystem[str(tmp_path / "codex-auth")] == "deny"
        assert filesystem["/app"] == "deny"
        assert filesystem["/proc"] == "deny"
        assert runtime_config["permissions"]["calendar-runtime-read-only"]["network"] == {
            "enabled": False
        }
        assert "sandbox" not in captured["run_options"]
        assert captured["run_options"]["output_schema"] == READ_ONLY_OUTPUT_SCHEMA
        assert set(READ_ONLY_OUTPUT_SCHEMA["required"]) == {"message", "proposal"}
        assert "Do not call shell, filesystem, web, app, MCP, or other tools" in (
            captured["prompt"]
        )
        assert '\"request_document\":\"# Request\"' in captured["prompt"]
    assert not Path(root).exists()


def test_runtime_tool_detection_fails_closed() -> None:
    plain_result = SimpleNamespace(
        items=[SimpleNamespace(root=SimpleNamespace(type="agentMessage"))]
    )
    tool_result = SimpleNamespace(
        items=[SimpleNamespace(root=SimpleNamespace(type="commandExecution"))]
    )

    assert _used_runtime_tool(plain_result) is False
    assert _used_runtime_tool(tool_result) is True


async def test_device_login_uses_private_persistent_auth_home_and_reports_account(
    monkeypatch,
    tmp_path,
) -> None:
    captured = {"configs": []}
    login_finished = asyncio.Event()

    class FakeHandle:
        login_id = "login-123"
        verification_url = "https://auth.openai.com/codex/device"
        user_code = "ABCD-EFGH"

        async def wait(self):
            await login_finished.wait()
            auth_home = Path(captured["configs"][0].env["CODEX_HOME"])
            (auth_home / "auth.json").write_text("{}")
            return SimpleNamespace(success=True)

    class FakeAsyncCodex:
        def __init__(self, config):
            self.config = config
            captured["configs"].append(config)

        async def __aenter__(self):
            return self

        async def close(self):
            return None

        async def login_chatgpt_device_code(self):
            return FakeHandle()

        async def account(self):
            account = SimpleNamespace(
                type="chatgpt",
                email="owner@example.test",
                plan_type=SimpleNamespace(value="plus"),
            )
            return SimpleNamespace(account=SimpleNamespace(root=account))

    monkeypatch.setattr("app.codex_runtime.adapter.AsyncCodex", FakeAsyncCodex)
    auth_home = tmp_path / "persistent-codex-auth"
    manager = CodexAuthManager(Settings(codex_auth_home=auth_home))

    started = await manager.start_device_login()

    assert started.status == "pending"
    assert started.verification_url == "https://auth.openai.com/codex/device"
    auth_config = captured["configs"][0]
    assert auth_config.env == {
        "PATH": auth_config.env["PATH"],
        "LANG": "C.UTF-8",
        "HOME": auth_config.env["HOME"],
        "CODEX_HOME": str(auth_home),
        "TMPDIR": auth_config.env["TMPDIR"],
    }
    assert "DATABASE_URL" not in auth_config.env
    assert 'cli_auth_credentials_store="file"' in auth_config.config_overrides
    assert 'forced_login_method="chatgpt"' in auth_config.config_overrides

    login_finished.set()
    for _ in range(20):
        if (await manager.get_device_login(started.login_id)).status == "completed":
            break
        await asyncio.sleep(0)
    completed = await manager.get_device_login(started.login_id)
    account = await manager.account_status()

    assert completed.status == "completed"
    assert account.authenticated is True
    assert account.auth_type == "chatgpt"
    assert account.email == "owner@example.test"
    assert account.plan_type == "plus"
    assert auth_home.stat().st_mode & 0o777 == 0o700
    await manager.shutdown()


def test_read_only_parser_rejects_proposals_unknown_fields_and_blank_answers() -> None:
    assert (
        parse_read_only_answer(
            json.dumps({"message": "Nothing is scheduled.", "proposal": None})
        ).message
        == "Nothing is scheduled."
    )

    invalid_responses = [
        {"message": "A proposal field is still required."},
        {"message": "I will change it.", "proposal": {"operation": "update_event"}},
        {"message": "An answer", "proposal": None, "reasoning": "hidden"},
        {"message": "   ", "proposal": None},
    ]
    for response in invalid_responses:
        with pytest.raises(InvalidAssistantResponseError):
            parse_read_only_answer(json.dumps(response))
