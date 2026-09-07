from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.inbox.models import MailQuarantine
from app.integrations.models import IntegrationConnection, MailSyncCursor


class IntegrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_mail(self, *, for_update: bool = False) -> IntegrationConnection | None:
        statement = select(IntegrationConnection).where(IntegrationConnection.kind == "mail")
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def upsert_mail(self, values: dict[str, Any]) -> IntegrationConnection:
        connection = await self.get_mail(for_update=True)
        if connection is None:
            connection = IntegrationConnection(kind="mail", **values)
            self.session.add(connection)
            await self.session.flush()
            cursor = MailSyncCursor(connection_id=connection.id)
            self.session.add(cursor)
        else:
            for key, value in values.items():
                setattr(connection, key, value)
        await self.session.flush()
        return connection

    async def get_cursor(self, connection_id, *, for_update: bool = False) -> MailSyncCursor:
        statement = select(MailSyncCursor).where(MailSyncCursor.connection_id == connection_id)
        if for_update:
            statement = statement.with_for_update()
        cursor = await self.session.scalar(statement)
        if cursor is None:
            cursor = MailSyncCursor(connection_id=connection_id)
            self.session.add(cursor)
            await self.session.flush()
        return cursor

    async def due_mail_connection(self, now: datetime) -> bool:
        statement = (
            select(MailSyncCursor.connection_id)
            .join(IntegrationConnection)
            .where(
                IntegrationConnection.kind == "mail",
                IntegrationConnection.credential_ref.is_not(None),
                MailSyncCursor.next_check_at.is_not(None),
                MailSyncCursor.next_check_at <= now,
            )
        )
        return await self.session.scalar(statement) is not None

    async def quarantine_count(self, connection_id) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(MailQuarantine)
                .where(MailQuarantine.connection_id == connection_id)
            )
            or 0
        )
