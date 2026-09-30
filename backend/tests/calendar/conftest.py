from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import engine, session_factory
from app.module_host import create_module_host


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    """Reset only Calendar-owned tables in the isolated focused database."""

    settings = get_settings()
    if not settings.testing:
        raise RuntimeError("Refusing to truncate Calendar data without TESTING=true.")
    async with engine.begin() as connection:
        database_name = await connection.scalar(text("SELECT current_database()"))
        if not str(database_name).endswith("_test"):
            raise RuntimeError(
                "Refusing to truncate a database whose name does not end with '_test'."
            )
        await connection.execute(text("TRUNCATE TABLE events, calendars CASCADE"))
    yield


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as database_session:
        yield database_session


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Exercise Calendar through the dependency-closed real module host."""

    transport = ASGITransport(app=create_module_host("calendar"))
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
