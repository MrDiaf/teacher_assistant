import asyncio
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import engine, session_factory
from app.module_host import create_module_host


@pytest_asyncio.fixture(autouse=True)
async def clean_database(tmp_path: Path) -> AsyncIterator[None]:
    """Reset only Courses state and its Calendar dependency; isolate course files."""

    settings = get_settings()
    if not settings.testing:
        raise RuntimeError("Refusing to run destructive Courses fixtures without TESTING=true.")
    async with engine.begin() as connection:
        database_name = await connection.scalar(text("SELECT current_database()"))
        if not str(database_name).endswith("_test"):
            raise RuntimeError(
                "Refusing to truncate a database whose name does not end with '_test'."
            )
        await connection.execute(
            text(
                "TRUNCATE TABLE note_summaries, note_source_links, notes, "
                "course_source_text, course_sources, course_calendar_links, "
                "courses, events, calendars CASCADE"
            )
        )

    previous_root = settings.course_storage_root
    isolated_root = tmp_path / "course-content"
    isolated_root.mkdir(mode=0o700)
    settings.course_storage_root = isolated_root
    try:
        yield
    finally:
        settings.course_storage_root = previous_root
        await asyncio.to_thread(shutil.rmtree, isolated_root, True)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as database_session:
        yield database_session


@pytest.fixture
def host_app() -> FastAPI:
    """The dependency-closed real module host: Platform, Calendar, and Courses."""

    return create_module_host("courses")


@pytest_asyncio.fixture
async def client(host_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Exercise Courses through its focused host instead of the full application."""

    transport = ASGITransport(app=host_app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
