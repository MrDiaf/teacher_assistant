from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import engine, session_factory
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE events, calendars CASCADE"))
    yield


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as database_session:
        yield database_session


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
