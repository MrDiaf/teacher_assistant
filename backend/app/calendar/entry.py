"""Public backend entry for Calendar routes."""

from app.calendar.import_routes import router as import_router
from app.calendar.routes import router as calendar_router
from app.calendar.subscription_routes import router as subscription_router
from app.calendar.subscription_scheduler import subscription_scheduler
from app.platform.modules.backend_contract import (
    BackendModuleEntry,
    RouterCodeContribution,
    background_task_lifecycle,
)

calendar_backend_entry = BackendModuleEntry(
    id="calendar",
    routers=(
        RouterCodeContribution(id="calendar", router=calendar_router, tags=("calendar",)),
        RouterCodeContribution(
            id="calendar-import", router=import_router, tags=("calendar-import",)
        ),
        RouterCodeContribution(
            id="calendar-subscription",
            router=subscription_router,
            tags=("calendar-subscription",),
        ),
    ),
    lifecycle=(
        background_task_lifecycle(
            id="ics-subscription-refresh",
            runner=subscription_scheduler,
            order=60,
        ),
    ),
)
