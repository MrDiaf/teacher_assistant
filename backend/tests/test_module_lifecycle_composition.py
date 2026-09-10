import asyncio

import pytest

from app.platform.modules.backend_catalog import registered_backend_modules
from app.platform.modules.backend_contract import (
    BackendLifecycleShutdownError,
    BackendModuleEntry,
    BackendModuleEntryError,
    LifecycleCodeContribution,
    backend_module_lifespan,
    background_task_lifecycle,
)


def _entry(
    module_id: str,
    *lifecycle: LifecycleCodeContribution,
) -> BackendModuleEntry:
    return BackendModuleEntry(id=module_id, lifecycle=lifecycle)


def test_production_lifecycle_bindings_preserve_effect_order() -> None:
    contributions = sorted(
        (contribution for entry in registered_backend_modules for contribution in entry.lifecycle),
        key=lambda contribution: contribution.order,
    )

    assert [contribution.id for contribution in contributions] == [
        "codex-auth",
        "assistant-execution",
        "mail-credential-root",
        "mail-storage-root",
        "document-storage-root",
        "ics-subscription-refresh",
        "mail-sync",
    ]


@pytest.mark.asyncio
async def test_selected_module_assembly_starts_only_selected_hooks() -> None:
    events: list[str] = []

    def contribution(hook_id: str, order: int) -> LifecycleCodeContribution:
        async def startup():
            events.append(f"start:{hook_id}")

            async def shutdown() -> None:
                events.append(f"stop:{hook_id}")

            return shutdown

        return LifecycleCodeContribution(id=hook_id, startup=startup, order=order)

    selected = _entry("selected", contribution("selected-hook", 10))
    _unselected = _entry("unselected", contribution("unselected-hook", 20))

    async with backend_module_lifespan((selected,)):
        assert events == ["start:selected-hook"]

    assert events == ["start:selected-hook", "stop:selected-hook"]


@pytest.mark.asyncio
async def test_normal_shutdown_cleans_hooks_in_reverse_start_order() -> None:
    events: list[str] = []

    def contribution(hook_id: str, order: int) -> LifecycleCodeContribution:
        async def startup():
            events.append(f"start:{hook_id}")

            async def shutdown() -> None:
                events.append(f"stop:{hook_id}")

            return shutdown

        return LifecycleCodeContribution(id=hook_id, startup=startup, order=order)

    entries = (
        _entry("later", contribution("later", 20)),
        _entry("earlier", contribution("earlier", 10)),
    )

    async with backend_module_lifespan(entries):
        assert events == ["start:earlier", "start:later"]

    assert events == ["start:earlier", "start:later", "stop:later", "stop:earlier"]


@pytest.mark.asyncio
async def test_application_error_still_cleans_hooks_and_preserves_error() -> None:
    stopped = False

    async def startup():
        async def shutdown() -> None:
            nonlocal stopped
            stopped = True

        return shutdown

    with pytest.raises(RuntimeError, match="application failed"):
        async with backend_module_lifespan(
            (_entry("fixture", LifecycleCodeContribution(id="hook", startup=startup, order=10)),)
        ):
            raise RuntimeError("application failed")

    assert stopped


@pytest.mark.asyncio
async def test_failed_shutdown_does_not_skip_earlier_cleanup() -> None:
    earlier_stopped = False

    async def earlier_startup():
        async def shutdown() -> None:
            nonlocal earlier_stopped
            earlier_stopped = True

        return shutdown

    async def failing_startup():
        async def shutdown() -> None:
            raise RuntimeError("shutdown failed")

        return shutdown

    entries = (
        _entry(
            "earlier",
            LifecycleCodeContribution(id="earlier", startup=earlier_startup, order=10),
        ),
        _entry(
            "failing",
            LifecycleCodeContribution(id="failing", startup=failing_startup, order=20),
        ),
    )

    with pytest.raises(BackendLifecycleShutdownError, match="failing"):
        async with backend_module_lifespan(entries):
            pass

    assert earlier_stopped


@pytest.mark.asyncio
async def test_invalid_cleanup_triggers_cleanup_of_earlier_hooks() -> None:
    earlier_stopped = False

    async def earlier_startup():
        async def shutdown() -> None:
            nonlocal earlier_stopped
            earlier_stopped = True

        return shutdown

    async def invalid_startup():
        return "not a cleanup callback"

    entries = (
        _entry(
            "earlier",
            LifecycleCodeContribution(id="earlier", startup=earlier_startup, order=10),
        ),
        _entry(
            "invalid",
            LifecycleCodeContribution(id="invalid", startup=invalid_startup, order=20),
        ),
    )

    with pytest.raises(BackendModuleEntryError, match="invalid cleanup callback"):
        async with backend_module_lifespan(entries):
            pytest.fail("invalid startup result must prevent application entry")

    assert earlier_stopped


@pytest.mark.asyncio
async def test_background_task_lifecycle_signals_and_cancels_runner() -> None:
    started = asyncio.Event()
    stopped = asyncio.Event()
    stop_was_set = False

    async def runner(stop: asyncio.Event) -> None:
        nonlocal stop_was_set
        started.set()
        try:
            await stop.wait()
        finally:
            stop_was_set = stop.is_set()
            stopped.set()

    contribution = background_task_lifecycle(id="runner", runner=runner, order=10)

    async with backend_module_lifespan((_entry("fixture", contribution),)):
        async with asyncio.timeout(0.5):
            await started.wait()

    async with asyncio.timeout(0.5):
        await stopped.wait()
    assert stop_was_set


@pytest.mark.asyncio
async def test_startup_failure_cleans_started_hooks_in_reverse_order() -> None:
    events: list[str] = []

    def successful(hook_id: str, order: int) -> LifecycleCodeContribution:
        async def startup():
            events.append(f"start:{hook_id}")

            async def shutdown() -> None:
                events.append(f"stop:{hook_id}")

            return shutdown

        return LifecycleCodeContribution(id=hook_id, startup=startup, order=order)

    async def failing_startup():
        events.append("start:failing")
        raise RuntimeError("startup failed")

    entries = (
        _entry("first", successful("first", 10)),
        _entry("second", successful("second", 20)),
        _entry(
            "failing",
            LifecycleCodeContribution(id="failing", startup=failing_startup, order=30),
        ),
    )

    with pytest.raises(RuntimeError, match="startup failed"):
        async with backend_module_lifespan(entries):
            pytest.fail("startup failure must prevent application entry")

    assert events == [
        "start:first",
        "start:second",
        "start:failing",
        "stop:second",
        "stop:first",
    ]


@pytest.mark.asyncio
async def test_shutdown_timeout_is_bounded_and_does_not_skip_earlier_hooks() -> None:
    events: list[str] = []

    async def first_startup():
        async def shutdown() -> None:
            events.append("stop:first")

        return shutdown

    async def stuck_startup():
        async def shutdown() -> None:
            events.append("stop:stuck")
            await asyncio.Event().wait()

        return shutdown

    entries = (
        _entry(
            "first",
            LifecycleCodeContribution(id="first", startup=first_startup, order=10),
        ),
        _entry(
            "stuck",
            LifecycleCodeContribution(
                id="stuck",
                startup=stuck_startup,
                order=20,
                shutdown_timeout_seconds=0.01,
            ),
        ),
    )

    with pytest.raises(BackendLifecycleShutdownError, match="stuck"):
        async with asyncio.timeout(0.5):
            async with backend_module_lifespan(entries):
                pass

    assert events == ["stop:stuck", "stop:first"]


@pytest.mark.asyncio
async def test_startup_failure_preserves_original_error_after_bounded_cleanup() -> None:
    earlier_stopped = False

    async def earlier_startup():
        async def shutdown() -> None:
            nonlocal earlier_stopped
            earlier_stopped = True

        return shutdown

    async def stuck_startup():
        async def shutdown() -> None:
            await asyncio.Event().wait()

        return shutdown

    async def failing_startup():
        raise RuntimeError("original startup error")

    entries = (
        _entry(
            "earlier",
            LifecycleCodeContribution(id="earlier", startup=earlier_startup, order=10),
        ),
        _entry(
            "stuck",
            LifecycleCodeContribution(
                id="stuck",
                startup=stuck_startup,
                order=20,
                shutdown_timeout_seconds=0.01,
            ),
        ),
        _entry(
            "failing",
            LifecycleCodeContribution(id="failing", startup=failing_startup, order=30),
        ),
    )

    with pytest.raises(RuntimeError, match="original startup error"):
        async with asyncio.timeout(0.5):
            async with backend_module_lifespan(entries):
                pytest.fail("startup failure must prevent application entry")

    assert earlier_stopped
