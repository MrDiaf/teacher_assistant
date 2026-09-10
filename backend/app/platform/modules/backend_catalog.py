"""Explicit production backend module entries and router assembly."""

from fastapi import FastAPI

from app.assistant.entry import assistant_backend_entry
from app.calendar.entry import calendar_backend_entry
from app.courses.entry import courses_backend_entry
from app.documents.entry import documents_backend_entry
from app.inbox.entry import inbox_backend_entry
from app.platform.entry import platform_backend_entry
from app.platform.modules.backend_contract import assemble_backend_modules, include_module_routers
from app.platform.modules.catalog import module_catalog

backend_module_entries = (
    platform_backend_entry,
    calendar_backend_entry,
    courses_backend_entry,
    inbox_backend_entry,
    documents_backend_entry,
    assistant_backend_entry,
)

registered_backend_modules = assemble_backend_modules(module_catalog, backend_module_entries)


def include_registered_routers(app: FastAPI) -> None:
    include_module_routers(app, registered_backend_modules)
