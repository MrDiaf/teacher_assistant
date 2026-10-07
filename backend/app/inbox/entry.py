"""Public backend entry for Inbox-owned routes."""

from app.core.config import get_settings
from app.inbox.integrations.credentials import IntegrationCredentialStore
from app.inbox.integrations.routes import router as integration_router
from app.inbox.mail_storage import MailStorage
from app.inbox.recovery import inbox_recovery_contribution
from app.inbox.routes import router as inbox_router
from app.inbox.scheduler import mail_scheduler
from app.platform.modules.backend_contract import (
    BackendModuleEntry,
    LifecycleCodeContribution,
    RouterCodeContribution,
    background_task_lifecycle,
)

__all__ = ["inbox_backend_entry", "inbox_recovery_contribution"]


async def _ensure_mail_credential_root() -> None:
    settings = get_settings()
    await IntegrationCredentialStore(settings.integration_credential_root).ensure_root()


async def _ensure_mail_storage_root() -> None:
    settings = get_settings()
    await MailStorage(
        settings.mail_storage_root,
        settings.mail_max_total_storage_bytes,
    ).ensure_root()

inbox_backend_entry = BackendModuleEntry(
    id="inbox",
    routers=(
        RouterCodeContribution(id="inbox", router=inbox_router, tags=("inbox",)),
        RouterCodeContribution(
            id="mail-integration", router=integration_router, tags=("integrations",)
        ),
    ),
    lifecycle=(
        LifecycleCodeContribution(
            id="mail-credential-root",
            startup=_ensure_mail_credential_root,
            order=30,
        ),
        LifecycleCodeContribution(
            id="mail-storage-root",
            startup=_ensure_mail_storage_root,
            order=40,
        ),
        background_task_lifecycle(
            id="mail-sync",
            runner=mail_scheduler,
            order=70,
        ),
    ),
)
