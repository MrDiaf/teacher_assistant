from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from app.database.session import session_factory
from app.inbox.integrations.mail.sync import MailSyncService
from app.inbox.integrations.repository import IntegrationRepository
from app.inbox.service import InboxService

SCHEDULER_TICK_SECONDS = 30
logger = logging.getLogger(__name__)


async def check_due_mail() -> None:
    async with session_factory() as session:
        await InboxService(session).retry_pending_cleanup()
        due = await IntegrationRepository(session).due_mail_connection(datetime.now(UTC))
    if not due:
        return
    try:
        async with session_factory() as session:
            await MailSyncService(session).sync()
    except Exception as exc:
        logger.error("mail_scheduler_check_failed error_type=%s", type(exc).__name__)


async def mail_scheduler(stop: asyncio.Event) -> None:
    while not stop.is_set():
        await check_due_mail()
        try:
            await asyncio.wait_for(stop.wait(), timeout=SCHEDULER_TICK_SECONDS)
        except TimeoutError:
            continue
