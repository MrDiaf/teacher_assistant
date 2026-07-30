from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from contextlib import suppress
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Protocol

from openai_codex import (
    ApprovalMode,
    AsyncCodex,
    CodexConfig,
    CodexError,
)

from app.codex_runtime.workspace import RuntimeWorkspace, safe_runtime_environment
from app.core.config import Settings, get_settings
from app.core.errors import (
    AssistantAuthError,
    AssistantLoginAttemptNotFoundError,
    AssistantNotConfiguredError,
    AssistantRuntimeError,
)


@dataclass(frozen=True)
class CodexRuntimeResult:
    final_response: str | None


@dataclass(frozen=True)
class CodexAccountStatus:
    authenticated: bool
    auth_type: Literal["chatgpt", "api_key"] | None = None
    email: str | None = None
    plan_type: str | None = None


@dataclass(frozen=True)
class CodexDeviceLoginAttempt:
    login_id: str
    verification_url: str
    user_code: str
    status: Literal["pending", "completed", "failed"] = "pending"
    safe_error: str | None = None


class CodexAdapter(Protocol):
    async def answer(
        self,
        workspace: RuntimeWorkspace,
        model: str | None = None,
    ) -> CodexRuntimeResult: ...


class CodexAuth(Protocol):
    async def account_status(self) -> CodexAccountStatus: ...

    async def start_device_login(self) -> CodexDeviceLoginAttempt: ...

    async def get_device_login(self, login_id: str) -> CodexDeviceLoginAttempt: ...

    async def logout(self) -> CodexAccountStatus: ...


def _secret_api_key(settings: Settings) -> str:
    if settings.openai_api_key is None:
        return ""
    return settings.openai_api_key.get_secret_value().strip()


def _prepare_auth_home(settings: Settings) -> Path:
    auth_home = settings.codex_auth_home
    auth_home.mkdir(mode=0o700, parents=True, exist_ok=True)
    auth_home.chmod(0o700)
    return auth_home


def _has_cached_chatgpt_credentials(auth_home: Path) -> bool:
    return (auth_home / "auth.json").is_file()


class CodexSdkAdapter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def answer(
        self,
        workspace: RuntimeWorkspace,
        model: str | None = None,
    ) -> CodexRuntimeResult:
        api_key = _secret_api_key(self.settings)
        auth_home = _prepare_auth_home(self.settings)
        has_chatgpt_credentials = _has_cached_chatgpt_credentials(auth_home)
        if not has_chatgpt_credentials and not api_key:
            raise AssistantNotConfiguredError()

        config = CodexConfig(
            cwd=str(workspace.job_directory),
            env=safe_runtime_environment(
                workspace,
                auth_home,
                None if has_chatgpt_credentials else api_key,
            ),
            config_overrides=(
                "allow_login_shell=false",
                'cli_auth_credentials_store="file"',
                'shell_environment_policy.inherit="none"',
                'shell_environment_policy.include_only=["PATH","HOME"]',
                "features.shell_tool=false",
                "features.unified_exec=false",
                "features.apps=false",
                "features.remote_plugin=false",
                "features.multi_agent=false",
                'web_search="disabled"',
            ),
            client_name="teacher-assistant",
            client_title="Teacher Assistant Calendar Runtime",
            client_version="1.0.0",
        )
        runtime_permissions = {
            "default_permissions": "calendar-runtime-read-only",
            "permissions": {
                "calendar-runtime-read-only": {
                    "filesystem": {
                        ":minimal": "read",
                        ":workspace_roots": {".": "read"},
                        str(auth_home): "deny",
                        "/app": "deny",
                        "/proc": "deny",
                        "/run": "deny",
                        "/var/run": "deny",
                    },
                    "network": {"enabled": False},
                }
            },
        }
        try:
            async with asyncio.timeout(self.settings.codex_timeout_seconds):
                async with AsyncCodex(config) as codex:
                    thread = await codex.thread_start(
                        approval_mode=ApprovalMode.deny_all,
                        cwd=str(workspace.job_directory),
                        developer_instructions=workspace.policy,
                        ephemeral=True,
                        model=model or self.settings.codex_model,
                        config=runtime_permissions,
                    )
                    result = await thread.run(
                        workspace.prompt,
                        approval_mode=ApprovalMode.deny_all,
                        output_schema=workspace.output_schema,
                    )
                    if _used_runtime_tool(result):
                        raise AssistantRuntimeError(
                            "The calendar assistant attempted an unavailable runtime tool. "
                            "No calendar data changed. Retry safely."
                        )
        except AssistantRuntimeError:
            raise
        except TimeoutError as exc:
            raise AssistantRuntimeError(
                "The calendar assistant timed out. No calendar data changed."
            ) from exc
        except (CodexError, RuntimeError) as exc:
            raise AssistantRuntimeError() from exc
        return CodexRuntimeResult(final_response=result.final_response)


_RUNTIME_TOOL_ITEM_TYPES = frozenset(
    {
        "collabAgentToolCall",
        "commandExecution",
        "dynamicToolCall",
        "fileChange",
        "imageGeneration",
        "imageView",
        "mcpToolCall",
        "sleep",
        "subAgentActivity",
        "webSearch",
    }
)


def _used_runtime_tool(result: Any) -> bool:
    """Fail closed if a future Codex configuration exposes a runtime tool."""

    return any(
        getattr(getattr(item, "root", item), "type", None) in _RUNTIME_TOOL_ITEM_TYPES
        for item in getattr(result, "items", ())
    )


@dataclass
class _AuthProcess:
    root: Path
    codex: AsyncCodex

    async def close(self) -> None:
        try:
            await self.codex.close()
        finally:
            shutil.rmtree(self.root, ignore_errors=True)


class CodexAuthManager:
    """Own ChatGPT device login without exposing credentials to the browser."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._lock = asyncio.Lock()
        self._attempt: CodexDeviceLoginAttempt | None = None
        self._login_task: asyncio.Task[None] | None = None

    async def _open_process(self) -> _AuthProcess:
        auth_home = _prepare_auth_home(self.settings)
        root = Path(tempfile.mkdtemp(prefix="teacher-assistant-codex-auth-"))
        root.chmod(0o700)
        runtime_home = root / "home"
        temp_directory = root / "tmp"
        runtime_home.mkdir(mode=0o700)
        temp_directory.mkdir(mode=0o700)
        environment = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "HOME": str(runtime_home),
            "CODEX_HOME": str(auth_home),
            "TMPDIR": str(temp_directory),
        }
        config = CodexConfig(
            cwd=str(root),
            env=environment,
            config_overrides=(
                "allow_login_shell=false",
                'cli_auth_credentials_store="file"',
                'forced_login_method="chatgpt"',
                'web_search="disabled"',
            ),
            client_name="teacher-assistant-auth",
            client_title="Teacher Assistant ChatGPT Sign-in",
            client_version="1.0.0",
        )
        codex = AsyncCodex(config)
        try:
            await codex.__aenter__()
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise
        return _AuthProcess(root=root, codex=codex)

    async def account_status(self) -> CodexAccountStatus:
        auth_home = _prepare_auth_home(self.settings)
        if _has_cached_chatgpt_credentials(auth_home):
            process: _AuthProcess | None = None
            try:
                process = await self._open_process()
                response = await process.codex.account()
            except (CodexError, OSError) as exc:
                raise AssistantAuthError() from exc
            finally:
                if process is not None:
                    await process.close()
            if response.account is not None:
                account = response.account.root
                if getattr(account, "type", None) == "chatgpt":
                    plan = getattr(account, "plan_type", None)
                    return CodexAccountStatus(
                        authenticated=True,
                        auth_type="chatgpt",
                        email=getattr(account, "email", None),
                        plan_type=getattr(plan, "value", None),
                    )

        if _secret_api_key(self.settings):
            return CodexAccountStatus(authenticated=True, auth_type="api_key")
        return CodexAccountStatus(authenticated=False)

    async def start_device_login(self) -> CodexDeviceLoginAttempt:
        async with self._lock:
            if self._attempt is not None and self._attempt.status == "pending":
                return self._attempt

            process: _AuthProcess | None = None
            try:
                process = await self._open_process()
                handle = await process.codex.login_chatgpt_device_code()
            except (CodexError, OSError) as exc:
                if process is not None:
                    await process.close()
                raise AssistantAuthError() from exc

            self._attempt = CodexDeviceLoginAttempt(
                login_id=handle.login_id,
                verification_url=handle.verification_url,
                user_code=handle.user_code,
            )
            self._login_task = asyncio.create_task(
                self._finish_device_login(process, handle),
                name="codex-chatgpt-device-login",
            )
            return self._attempt

    async def _finish_device_login(self, process: _AuthProcess, handle: Any) -> None:
        try:
            notification = await handle.wait()
            async with self._lock:
                if self._attempt is None or self._attempt.login_id != handle.login_id:
                    return
                if notification.success:
                    self._attempt = replace(self._attempt, status="completed")
                else:
                    self._attempt = replace(
                        self._attempt,
                        status="failed",
                        safe_error="OpenAI did not complete sign-in. Start a new attempt.",
                    )
        except asyncio.CancelledError:
            raise
        except (CodexError, OSError):
            async with self._lock:
                if self._attempt is not None and self._attempt.login_id == handle.login_id:
                    self._attempt = replace(
                        self._attempt,
                        status="failed",
                        safe_error="ChatGPT sign-in expired or could not finish. Start again.",
                    )
        finally:
            await process.close()

    async def get_device_login(self, login_id: str) -> CodexDeviceLoginAttempt:
        async with self._lock:
            if self._attempt is None or self._attempt.login_id != login_id:
                raise AssistantLoginAttemptNotFoundError()
            return self._attempt

    async def logout(self) -> CodexAccountStatus:
        await self.shutdown()
        auth_home = _prepare_auth_home(self.settings)
        if _has_cached_chatgpt_credentials(auth_home):
            process: _AuthProcess | None = None
            try:
                process = await self._open_process()
                await process.codex.logout()
            except (CodexError, OSError) as exc:
                raise AssistantAuthError() from exc
            finally:
                if process is not None:
                    await process.close()
            (auth_home / "auth.json").unlink(missing_ok=True)
        async with self._lock:
            self._attempt = None
        return await self.account_status()

    async def shutdown(self) -> None:
        task = self._login_task
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self._login_task = None


def get_codex_adapter() -> CodexAdapter:
    return CodexSdkAdapter()


@lru_cache
def get_codex_auth_manager() -> CodexAuthManager:
    return CodexAuthManager()
