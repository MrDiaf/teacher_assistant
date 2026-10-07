"""Development host for one explicitly supported bundled module."""

from __future__ import annotations

import os

from fastapi import FastAPI

from app.assistant.entry import assistant_backend_entry
from app.calendar.entry import calendar_backend_entry
from app.courses.entry import courses_backend_entry
from app.documents.entry import documents_backend_entry
from app.inbox.entry import inbox_backend_entry
from app.platform.application import create_application
from app.platform.entry import platform_backend_entry
from app.platform.modules.backend_contract import (
    BackendModuleEntry,
    assemble_backend_modules,
)
from app.platform.modules.catalog import module_catalog
from app.platform.modules.contract import select_module_catalog

MODULE_HOST_ENV = "TEACHER_ASSISTANT_MODULE_HOST"
SUPPORTED_MODULE_HOST_IDS = ("assistant", "calendar", "courses", "documents", "inbox")


class ModuleHostError(ValueError):
    """Raised when a focused host is requested for an unsupported module."""


def assemble_module_host(module_id: str) -> tuple[BackendModuleEntry, ...]:
    if module_id not in SUPPORTED_MODULE_HOST_IDS:
        supported = ", ".join(SUPPORTED_MODULE_HOST_IDS)
        raise ModuleHostError(
            f"unsupported module host {module_id!r}; supported modules: {supported}"
        )
    selected_catalog = select_module_catalog(module_catalog, (module_id,))
    selected_ids = {registration.id for registration in selected_catalog.registrations}
    selected_entries = tuple(
        entry
        for entry in (
            platform_backend_entry,
            assistant_backend_entry,
            calendar_backend_entry,
            courses_backend_entry,
            documents_backend_entry,
            inbox_backend_entry,
        )
        if entry.id in selected_ids
    )
    return assemble_backend_modules(
        selected_catalog,
        selected_entries,
    )


def create_module_host(module_id: str) -> FastAPI:
    """Build the real shared API host with only one module dependency closure."""

    return create_application(assemble_module_host(module_id))


def create_module_host_from_environment() -> FastAPI:
    module_id = os.environ.get(MODULE_HOST_ENV, "").strip()
    if not module_id:
        raise ModuleHostError(f"{MODULE_HOST_ENV} must name a supported module")
    return create_module_host(module_id)
