from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import get_settings
from app.database.session import engine
from app.module_host import create_module_host


@pytest_asyncio.fixture(autouse=True)
async def clean_database(tmp_path: Path) -> AsyncIterator[None]:
    """Reset only Documents-owned state and use a private per-test source root."""

    settings = get_settings()
    if not settings.testing:
        raise RuntimeError("Refusing to run destructive Documents fixtures without TESTING=true.")
    async with engine.begin() as connection:
        database_name = await connection.scalar(text("SELECT current_database()"))
        if not str(database_name).endswith("_test"):
            raise RuntimeError(
                "Refusing to truncate a database whose name does not end with '_test'."
            )
        await connection.execute(
            text(
                "TRUNCATE TABLE document_project_tags, document_tags, "
                "document_projects CASCADE"
            )
        )

    previous_root = settings.document_storage_root
    isolated_root = tmp_path / "document-projects"
    isolated_root.mkdir(mode=0o700)
    settings.document_storage_root = isolated_root
    try:
        yield
    finally:
        settings.document_storage_root = previous_root


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Exercise Documents through the dependency-closed real module host."""

    transport = ASGITransport(app=create_module_host("documents"))
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
