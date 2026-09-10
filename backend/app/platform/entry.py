"""Public backend entry for Platform-owned routes."""

from fastapi import APIRouter
from sqlalchemy import text

from app.ai.routes import router as ai_router
from app.codex_runtime.adapter import get_codex_auth_manager
from app.database.session import session_factory
from app.diagnostics.routes import router as diagnostic_router
from app.platform.modules.backend_contract import (
    BackendModuleEntry,
    LifecycleCodeContribution,
    LifecycleShutdown,
    RouterCodeContribution,
)

system_router = APIRouter()


@system_router.get("/health")
async def health() -> dict[str, str]:
    async with session_factory() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}


async def _register_codex_auth_shutdown() -> LifecycleShutdown:
    return get_codex_auth_manager().shutdown


platform_backend_entry = BackendModuleEntry(
    id="platform",
    routers=(
        RouterCodeContribution(id="ai-models", router=ai_router, tags=("ai",)),
        RouterCodeContribution(id="diagnostics", router=diagnostic_router, tags=("diagnostics",)),
        RouterCodeContribution(
            id="system-health", router=system_router, prefix="", tags=("system",)
        ),
    ),
    lifecycle=(
        LifecycleCodeContribution(
            id="codex-auth",
            startup=_register_codex_auth_shutdown,
            order=10,
        ),
    ),
)
