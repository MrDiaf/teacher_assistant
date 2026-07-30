import asyncio
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import engine, session_factory
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    settings = get_settings()
    if not settings.testing:
        raise RuntimeError(
            "Refusing to run destructive database fixtures without TESTING=true."
        )
    async with engine.begin() as connection:
        database_name = await connection.scalar(text("SELECT current_database()"))
        if not str(database_name).endswith("_test"):
            raise RuntimeError(
                "Refusing to truncate a database whose name does not end with '_test'."
            )
        await connection.execute(
            text(
                "TRUNCATE TABLE note_summaries, assistant_proposal_actions, assistant_proposals, "
                "assistant_jobs, assistant_messages, "
                "assistant_conversations, note_source_links, notes, "
                "course_source_text, course_sources, course_calendar_links, "
                "courses, events, calendars CASCADE"
            )
        )
    storage_root = settings.course_storage_root.resolve()
    if storage_root in {Path("/"), Path.home().resolve()}:
        raise RuntimeError("Refusing to clear an unsafe course storage root.")
    await asyncio.to_thread(shutil.rmtree, storage_root, True)
    await asyncio.to_thread(
        storage_root.mkdir,
        parents=True,
        mode=0o700,
        exist_ok=True,
    )
    try:
        yield
    finally:
        await asyncio.to_thread(shutil.rmtree, storage_root, True)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as database_session:
        yield database_session


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
