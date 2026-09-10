import pytest
from fastapi import APIRouter, FastAPI

from app.platform.modules.backend_catalog import (
    include_registered_routers,
    registered_backend_modules,
)
from app.platform.modules.backend_contract import (
    BackendModuleEntry,
    BackendModuleEntryError,
    LifecycleCodeContribution,
    RouterCodeContribution,
    assemble_backend_modules,
    include_module_routers,
)
from app.platform.modules.contract import (
    ModuleCatalog,
    ModuleContributions,
    ModuleRegistration,
)


def _fixture_catalog(
    *route_ids: str,
    lifecycle_ids: tuple[str, ...] = (),
) -> ModuleCatalog:
    return ModuleCatalog(
        (
            ModuleRegistration(
                id="fixture",
                display_name="Fixture",
                order=0,
                enabled_by_default=True,
                capabilities=("api",),
                dependencies=(),
                contributions=ModuleContributions(
                    routes=route_ids,
                    pages=(),
                    settings_panels=(),
                    lifecycle=lifecycle_ids,
                ),
            ),
        )
    )


def test_production_backend_entries_match_catalog_order() -> None:
    assert [entry.id for entry in registered_backend_modules] == [
        "platform",
        "calendar",
        "courses",
        "inbox",
        "documents",
        "assistant",
    ]
    assert [
        contribution.id for entry in registered_backend_modules for contribution in entry.routers
    ] == [
        "ai-models",
        "diagnostics",
        "system-health",
        "calendar",
        "calendar-import",
        "calendar-subscription",
        "courses",
        "course-calendars",
        "course-materials",
        "course-notes",
        "course-note-prettify",
        "course-note-summaries",
        "mail-integration",
        "inbox",
        "documents",
        "assistant",
    ]


def test_registered_routers_can_be_attached_to_a_fresh_fastapi_app() -> None:
    composed_app = FastAPI()

    include_registered_routers(composed_app)

    paths = {route.path for route in composed_app.routes}
    assert "/health" in paths
    assert "/api/v1/calendars" in paths
    assert "/api/v1/courses" in paths
    assert "/api/v1/inbox" in paths
    assert "/api/v1/document-projects" in paths
    assert "/api/v1/assistant/conversations" in paths


def test_fixture_router_assembles_without_production_modules() -> None:
    fixture_router = APIRouter()

    @fixture_router.get("/fixture")
    async def fixture() -> dict[str, bool]:
        return {"ok": True}

    entries = assemble_backend_modules(
        _fixture_catalog("fixture-router"),
        (
            BackendModuleEntry(
                id="fixture",
                routers=(RouterCodeContribution(id="fixture-router", router=fixture_router),),
            ),
        ),
    )
    composed_app = FastAPI()
    include_module_routers(composed_app, entries)

    assert entries[0].routers[0].router is fixture_router
    assert "/api/v1/fixture" in {route.path for route in composed_app.routes}


def test_missing_router_code_contribution_is_rejected() -> None:
    with pytest.raises(BackendModuleEntryError, match="missing router code contributions"):
        assemble_backend_modules(
            _fixture_catalog("required-router"),
            (BackendModuleEntry(id="fixture", routers=()),),
        )


def test_missing_lifecycle_code_contribution_is_rejected() -> None:
    with pytest.raises(BackendModuleEntryError, match="missing lifecycle code contributions"):
        assemble_backend_modules(
            _fixture_catalog(lifecycle_ids=("required-hook",)),
            (BackendModuleEntry(id="fixture"),),
        )


def test_duplicate_lifecycle_orders_are_rejected() -> None:
    async def startup():
        return None

    with pytest.raises(BackendModuleEntryError, match="duplicate lifecycle order 10"):
        assemble_backend_modules(
            _fixture_catalog(lifecycle_ids=("first", "second")),
            (
                BackendModuleEntry(
                    id="fixture",
                    lifecycle=(
                        LifecycleCodeContribution(id="first", startup=startup, order=10),
                        LifecycleCodeContribution(id="second", startup=startup, order=10),
                    ),
                ),
            ),
        )


def test_duplicate_http_method_and_path_are_rejected() -> None:
    first_router = APIRouter()
    second_router = APIRouter()

    @first_router.get("/same")
    async def first() -> None:
        return None

    @second_router.get("/same")
    async def second() -> None:
        return None

    with pytest.raises(BackendModuleEntryError, match="duplicate backend route GET"):
        assemble_backend_modules(
            _fixture_catalog("first", "second"),
            (
                BackendModuleEntry(
                    id="fixture",
                    routers=(
                        RouterCodeContribution(id="first", router=first_router),
                        RouterCodeContribution(id="second", router=second_router),
                    ),
                ),
            ),
        )
