"""Public backend entry for Documents code contributions."""

from app.core.config import get_settings
from app.documents.recovery import documents_recovery_contribution
from app.documents.routes import router as document_router
from app.documents.storage import DocumentStorage
from app.platform.modules.backend_contract import (
    BackendModuleEntry,
    LifecycleCodeContribution,
    RouterCodeContribution,
)

__all__ = ["documents_backend_entry", "documents_recovery_contribution"]


async def _ensure_document_storage_root() -> None:
    settings = get_settings()
    await DocumentStorage(
        settings.document_storage_root,
        settings.document_max_source_bytes,
    ).ensure_root()

documents_backend_entry = BackendModuleEntry(
    id="documents",
    routers=(RouterCodeContribution(id="documents", router=document_router, tags=("documents",)),),
    lifecycle=(
        LifecycleCodeContribution(
            id="document-storage-root",
            startup=_ensure_document_storage_root,
            order=50,
        ),
    ),
)
