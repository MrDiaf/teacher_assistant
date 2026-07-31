from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any
from uuid import UUID


class AssistantExecutionRegistry:
    """Tracks in-process Assistant jobs so an owner cancellation can stop Codex."""

    def __init__(self) -> None:
        self._tasks: dict[UUID, asyncio.Task[Any]] = {}

    def register(self, job_id: UUID, task: asyncio.Task[Any]) -> None:
        self._tasks[job_id] = task

    def unregister(self, job_id: UUID, task: asyncio.Task[Any]) -> None:
        if self._tasks.get(job_id) is task:
            self._tasks.pop(job_id, None)

    def cancel(self, job_id: UUID) -> bool:
        task = self._tasks.get(job_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    async def shutdown(self) -> None:
        tasks = [task for task in self._tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()


assistant_execution_registry = AssistantExecutionRegistry()
