"""Typed bindings between module metadata and explicit backend code entries."""

from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from app.platform.modules.contract import ModuleCatalog

logger = logging.getLogger(__name__)

type LifecycleShutdown = Callable[[], Awaitable[None]]
type LifecycleStartup = Callable[[], Awaitable[LifecycleShutdown | None]]


class BackendModuleEntryError(ValueError):
    """Raised when backend code entries do not match validated metadata."""


class BackendLifecycleShutdownError(RuntimeError):
    """Raised after every lifecycle cleanup was attempted but one or more failed."""


@dataclass(frozen=True, slots=True)
class RouterCodeContribution:
    id: str
    router: APIRouter
    prefix: str = "/api/v1"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LifecycleCodeContribution:
    """Start one hook and optionally return its idempotent cleanup callback."""

    id: str
    startup: LifecycleStartup
    order: int
    shutdown_timeout_seconds: float = 5.0


@dataclass(frozen=True, slots=True)
class BackendModuleEntry:
    id: str
    routers: tuple[RouterCodeContribution, ...] = ()
    lifecycle: tuple[LifecycleCodeContribution, ...] = ()


def assemble_backend_modules(
    catalog: ModuleCatalog,
    entries: tuple[BackendModuleEntry, ...],
) -> tuple[BackendModuleEntry, ...]:
    """Validate explicit code bindings and return them in metadata order."""

    entries_by_id: dict[str, BackendModuleEntry] = {}
    for entry in entries:
        if entry.id in entries_by_id:
            raise BackendModuleEntryError(f"duplicate backend module entry: {entry.id!r}")
        entries_by_id[entry.id] = entry

    known_module_ids = {registration.id for registration in catalog.registrations}
    unknown_module_ids = sorted(set(entries_by_id) - known_module_ids)
    if unknown_module_ids:
        raise BackendModuleEntryError(
            f"unknown backend module entries: {', '.join(unknown_module_ids)}"
        )

    assembled: list[BackendModuleEntry] = []
    for registration in catalog.registrations:
        entry = entries_by_id.get(registration.id)
        if entry is None:
            raise BackendModuleEntryError(f"missing backend module entry: {registration.id!r}")

        routers_by_id: dict[str, RouterCodeContribution] = {}
        for contribution in entry.routers:
            if contribution.id in routers_by_id:
                raise BackendModuleEntryError(
                    f"duplicate router code contribution {contribution.id!r} in module {entry.id!r}"
                )
            _validate_router_contribution(contribution, entry.id)
            routers_by_id[contribution.id] = contribution

        expected_router_ids = registration.contributions.routes
        unknown_router_ids = sorted(set(routers_by_id) - set(expected_router_ids))
        if unknown_router_ids:
            raise BackendModuleEntryError(
                f"unknown router code contributions for module {entry.id!r}: "
                f"{', '.join(unknown_router_ids)}"
            )
        missing_router_ids = [
            route_id for route_id in expected_router_ids if route_id not in routers_by_id
        ]
        if missing_router_ids:
            raise BackendModuleEntryError(
                f"missing router code contributions for module {entry.id!r}: "
                f"{', '.join(missing_router_ids)}"
            )

        lifecycle_by_id: dict[str, LifecycleCodeContribution] = {}
        for contribution in entry.lifecycle:
            if contribution.id in lifecycle_by_id:
                raise BackendModuleEntryError(
                    f"duplicate lifecycle code contribution {contribution.id!r} "
                    f"in module {entry.id!r}"
                )
            _validate_lifecycle_contribution(contribution, entry.id)
            lifecycle_by_id[contribution.id] = contribution

        expected_lifecycle_ids = registration.contributions.lifecycle
        unknown_lifecycle_ids = sorted(set(lifecycle_by_id) - set(expected_lifecycle_ids))
        if unknown_lifecycle_ids:
            raise BackendModuleEntryError(
                f"unknown lifecycle code contributions for module {entry.id!r}: "
                f"{', '.join(unknown_lifecycle_ids)}"
            )
        missing_lifecycle_ids = [
            lifecycle_id
            for lifecycle_id in expected_lifecycle_ids
            if lifecycle_id not in lifecycle_by_id
        ]
        if missing_lifecycle_ids:
            raise BackendModuleEntryError(
                f"missing lifecycle code contributions for module {entry.id!r}: "
                f"{', '.join(missing_lifecycle_ids)}"
            )

        assembled.append(
            BackendModuleEntry(
                id=entry.id,
                routers=tuple(routers_by_id[route_id] for route_id in expected_router_ids),
                lifecycle=tuple(
                    lifecycle_by_id[lifecycle_id] for lifecycle_id in expected_lifecycle_ids
                ),
            )
        )

    _validate_unique_routes(tuple(assembled))
    _validate_unique_lifecycle_orders(tuple(assembled))
    return tuple(assembled)


def include_module_routers(app: FastAPI, entries: tuple[BackendModuleEntry, ...]) -> None:
    """Attach an already validated entry set without consulting global state."""

    for module in entries:
        for contribution in module.routers:
            app.include_router(
                contribution.router,
                prefix=contribution.prefix,
                tags=list(contribution.tags),
            )


@asynccontextmanager
async def backend_module_lifespan(
    entries: tuple[BackendModuleEntry, ...],
) -> AsyncIterator[None]:
    """Start only the supplied modules and clean up every successfully started hook."""

    contributions = sorted(
        (
            contribution
            for entry in entries
            for contribution in entry.lifecycle
        ),
        key=lambda contribution: contribution.order,
    )
    cleanups: list[tuple[LifecycleCodeContribution, LifecycleShutdown]] = []
    try:
        for contribution in contributions:
            cleanup = await contribution.startup()
            if cleanup is not None:
                if not callable(cleanup):
                    raise BackendModuleEntryError(
                        f"lifecycle {contribution.id!r} returned an invalid cleanup callback"
                    )
                cleanups.append((contribution, cleanup))
    except BaseException:
        await _shutdown_lifecycle_hooks(cleanups, startup_failed=True)
        raise

    try:
        yield
    except BaseException:
        await _shutdown_lifecycle_hooks(cleanups, startup_failed=False)
        raise
    else:
        failures = await _shutdown_lifecycle_hooks(cleanups, startup_failed=False)
        if failures:
            failed_ids = ", ".join(failures)
            raise BackendLifecycleShutdownError(
                f"backend lifecycle shutdown failed for: {failed_ids}"
            )


def background_task_lifecycle(
    *,
    id: str,
    runner: Callable[[asyncio.Event], Awaitable[None]],
    order: int,
    shutdown_timeout_seconds: float = 5.0,
) -> LifecycleCodeContribution:
    """Build a lifecycle contribution for an existing cooperative scheduler."""

    async def startup() -> LifecycleShutdown:
        stop = asyncio.Event()
        task = asyncio.create_task(runner(stop), name=f"lifecycle:{id}")

        async def shutdown() -> None:
            stop.set()
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        return shutdown

    return LifecycleCodeContribution(
        id=id,
        startup=startup,
        order=order,
        shutdown_timeout_seconds=shutdown_timeout_seconds,
    )


def _validate_router_contribution(contribution: RouterCodeContribution, module_id: str) -> None:
    if contribution.prefix and (
        not contribution.prefix.startswith("/") or contribution.prefix.endswith("/")
    ):
        raise BackendModuleEntryError(
            f"router {contribution.id!r} in module {module_id!r} has invalid prefix "
            f"{contribution.prefix!r}"
        )


def _validate_lifecycle_contribution(
    contribution: LifecycleCodeContribution,
    module_id: str,
) -> None:
    if not callable(contribution.startup):
        raise BackendModuleEntryError(
            f"lifecycle {contribution.id!r} in module {module_id!r} has no startup callback"
        )
    if isinstance(contribution.order, bool) or not isinstance(contribution.order, int):
        raise BackendModuleEntryError(
            f"lifecycle {contribution.id!r} in module {module_id!r} has invalid order"
        )
    timeout = contribution.shutdown_timeout_seconds
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, int | float)
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise BackendModuleEntryError(
            f"lifecycle {contribution.id!r} in module {module_id!r} "
            "has invalid shutdown timeout"
        )


def _validate_unique_lifecycle_orders(entries: tuple[BackendModuleEntry, ...]) -> None:
    orders: dict[int, tuple[str, str]] = {}
    for entry in entries:
        for contribution in entry.lifecycle:
            existing = orders.get(contribution.order)
            if existing is not None:
                raise BackendModuleEntryError(
                    f"duplicate lifecycle order {contribution.order}: "
                    f"{existing[0]!r}/{existing[1]!r} and "
                    f"{entry.id!r}/{contribution.id!r}"
                )
            orders[contribution.order] = (entry.id, contribution.id)


async def _shutdown_lifecycle_hooks(
    cleanups: list[tuple[LifecycleCodeContribution, LifecycleShutdown]],
    *,
    startup_failed: bool,
) -> list[str]:
    failures: list[str] = []
    for contribution, cleanup in reversed(cleanups):
        try:
            shutdown_task = asyncio.create_task(
                cleanup(),
                name=f"lifecycle-shutdown:{contribution.id}",
            )
            done, _pending = await asyncio.wait(
                (shutdown_task,),
                timeout=contribution.shutdown_timeout_seconds,
            )
            if shutdown_task not in done:
                shutdown_task.cancel()
                shutdown_task.add_done_callback(_consume_task_result)
                raise TimeoutError
            await shutdown_task
        except Exception as exc:
            failures.append(contribution.id)
            logger.error(
                "backend_lifecycle_shutdown_failed lifecycle=%s startup_failed=%s error_type=%s",
                contribution.id,
                startup_failed,
                type(exc).__name__,
            )
    return failures


def _consume_task_result(task: asyncio.Task[Any]) -> None:
    with suppress(asyncio.CancelledError, Exception):
        task.result()


def _validate_unique_routes(entries: tuple[BackendModuleEntry, ...]) -> None:
    routes: dict[tuple[str, str], tuple[str, str]] = {}
    for entry in entries:
        for contribution in entry.routers:
            for route in contribution.router.routes:
                path = f"{contribution.prefix}{route.path}"
                methods = route.methods if isinstance(route, APIRoute) else {"WEBSOCKET"}
                for method in methods:
                    signature = (method, path)
                    existing = routes.get(signature)
                    if existing is not None:
                        raise BackendModuleEntryError(
                            f"duplicate backend route {method} {path!r}: "
                            f"{existing[0]!r}/{existing[1]!r} and "
                            f"{entry.id!r}/{contribution.id!r}"
                        )
                    routes[signature] = (entry.id, contribution.id)
