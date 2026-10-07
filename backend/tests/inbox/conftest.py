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
from app.module_host import create_module_host


@pytest_asyncio.fixture(autouse=True)
async def clean_database(tmp_path: Path) -> AsyncIterator[None]:
    """Reset only Inbox state and use isolated credential/attachment roots."""

    settings = get_settings()
    if not settings.testing:
        raise RuntimeError("Refusing to truncate Inbox tests without TESTING=true.")
    async with engine.begin() as connection:
        database_name = await connection.scalar(text("SELECT current_database()"))
        if not str(database_name).endswith("_test"):
            raise RuntimeError(
                "Refusing to truncate a database whose name does not end with '_test'."
            )
        await connection.execute(
            text(
                "TRUNCATE TABLE mail_cleanup_audits, mail_quarantines, "
                "mail_attachments, mail_addresses, mail_messages, mail_sync_cursors, "
                "mail_integration_connections CASCADE"
            )
        )

    previous_credentials = settings.integration_credential_root
    previous_attachments = settings.mail_storage_root
    credential_root = tmp_path / "integration-credentials"
    attachment_root = tmp_path / "mail-attachments"
    credential_root.mkdir(mode=0o700)
    attachment_root.mkdir(mode=0o700)
    settings.integration_credential_root = credential_root
    settings.mail_storage_root = attachment_root
    try:
        yield
    finally:
        settings.integration_credential_root = previous_credentials
        settings.mail_storage_root = previous_attachments
        await asyncio.to_thread(shutil.rmtree, credential_root, True)
        await asyncio.to_thread(shutil.rmtree, attachment_root, True)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as database_session:
        yield database_session


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=create_module_host("inbox"))
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
