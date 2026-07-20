from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from app.calendar.repository import CalendarRepository
from app.calendar.subscription_service import IcsSubscriptionService
from app.database.session import session_factory

CHECK_INTERVAL_SECONDS = 60 * 60
logger = logging.getLogger(__name__)


async def refresh_due_subscriptions() -> None:
    async with session_factory() as session:
        due_ids = [
            calendar.id
            for calendar in await CalendarRepository(session).list_due_subscriptions(
                datetime.now(UTC)
            )
        ]
    for calendar_id in due_ids:
        try:
            async with session_factory() as session:
                await IcsSubscriptionService(session).sync(calendar_id)
        except Exception as exc:
            logger.error(
                "ICS subscription refresh failed: calendar=%s error_type=%s",
                calendar_id,
                type(exc).__name__,
            )


async def subscription_scheduler(stop: asyncio.Event) -> None:
    while not stop.is_set():
        await refresh_due_subscriptions()
        try:
            await asyncio.wait_for(stop.wait(), timeout=CHECK_INTERVAL_SECONDS)
        except TimeoutError:
            continue
