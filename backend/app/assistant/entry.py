"""Public backend entry for Assistant routes."""

from app.assistant.execution import assistant_execution_registry
from app.assistant.routes import router as assistant_router
from app.platform.modules.backend_contract import (
    BackendModuleEntry,
    LifecycleCodeContribution,
    LifecycleShutdown,
    RouterCodeContribution,
)


async def _register_assistant_execution_shutdown() -> LifecycleShutdown:
    return assistant_execution_registry.shutdown

assistant_backend_entry = BackendModuleEntry(
    id="assistant",
    routers=(RouterCodeContribution(id="assistant", router=assistant_router, tags=("assistant",)),),
    lifecycle=(
        LifecycleCodeContribution(
            id="assistant-execution",
            startup=_register_assistant_execution_shutdown,
            order=20,
        ),
    ),
)
