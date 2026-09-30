from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.errors import IcsSubscriptionNotFoundError, InvalidIcsError
from app.calendar.ics import IcsIssue, ParsedIcsCalendar, parse_ics
from app.calendar.ics_fetch import fetch_ics
from app.calendar.import_service import IcsImportResult, IcsImportService
from app.calendar.models import Calendar
from app.calendar.repository import CalendarRepository, EventRepository
from app.core.errors import ApplicationError

SYNC_INTERVAL = timedelta(days=1)


@dataclass(frozen=True)
class IcsSyncResult:
    calendar: Calendar
    created_count: int
    updated_count: int
    deleted_count: int
    skipped_count: int


def prepare_subscription_calendar(parsed: ParsedIcsCalendar) -> ParsedIcsCalendar:
    events = []
    for event in parsed.events:
        if event.is_importable and event.uid is None:
            events.append(
                replace(
                    event,
                    issues=[
                        *event.issues,
                        IcsIssue(
                            severity="error",
                            message=(
                                "Subscribed events require a UID so updates can be matched safely."
                            ),
                        ),
                    ],
                )
            )
        else:
            events.append(event)
    return replace(parsed, events=events)


class IcsSubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.calendars = CalendarRepository(session)
        self.events = EventRepository(session)

    async def preview(self, url: str) -> ParsedIcsCalendar:
        return prepare_subscription_calendar(
            parse_ics(await fetch_ics(url), "Subscribed calendar.ics")
        )

    async def create(
        self,
        url: str,
        *,
        calendar_name: str | None,
        calendar_color: str,
    ) -> IcsImportResult:
        parsed = await self.preview(url)
        now = datetime.now(UTC)
        return await IcsImportService(self.session).import_calendar(
            parsed,
            destination_calendar_id=None,
            calendar_name=calendar_name,
            calendar_color=calendar_color,
            subscription_url=url.strip(),
            subscription_synced_at=now,
            subscription_next_sync_at=now + SYNC_INTERVAL,
        )

    async def sync(self, calendar_id: uuid.UUID) -> IcsSyncResult:
        calendar = await self.calendars.get(calendar_id)
        if not calendar.is_subscribed:
            raise IcsSubscriptionNotFoundError()

        try:
            parsed = prepare_subscription_calendar(
                parse_ics(
                    await fetch_ics(calendar.subscription_url or ""),
                    "Subscribed calendar.ics",
                )
            )
            if not any(event.is_importable for event in parsed.events):
                raise InvalidIcsError("The subscription contains no safely refreshable events.")
        except ApplicationError as exc:
            await self._record_failure(calendar_id, str(exc))
            raise

        calendar = await self.calendars.begin_subscription_sync(calendar_id)
        existing = {
            event.external_uid: event
            for event in await self.events.list_subscription_events(calendar_id)
            if event.external_uid is not None
        }
        seen_uids = {event.uid for event in parsed.events if event.uid is not None}
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for parsed_event in parsed.events:
            if not parsed_event.is_importable or parsed_event.uid is None:
                skipped_count += 1
                continue
            values = IcsImportService._event_values(calendar_id, parsed_event)
            current = existing.get(parsed_event.uid)
            if current is None:
                await self.events.sync_create(values)
                created_count += 1
                continue
            changes = {
                key: value
                for key, value in values.items()
                if key not in {"calendar_id", "external_uid"} and getattr(current, key) != value
            }
            if changes:
                await self.events.sync_update(current, changes)
                updated_count += 1

        removed = [event for uid, event in existing.items() if uid not in seen_uids]
        for event in removed:
            await self.events.sync_delete(event)

        now = datetime.now(UTC)
        calendar = await self.calendars.finish_subscription_sync(
            calendar,
            synced_at=now,
            next_sync_at=now + SYNC_INTERVAL,
        )
        await self.session.commit()
        await self.session.refresh(calendar)
        return IcsSyncResult(
            calendar=calendar,
            created_count=created_count,
            updated_count=updated_count,
            deleted_count=len(removed),
            skipped_count=skipped_count,
        )

    async def _record_failure(self, calendar_id: uuid.UUID, message: str) -> None:
        await self.session.rollback()
        await self.calendars.record_subscription_failure(
            calendar_id,
            message=message or "The subscription refresh failed.",
            next_sync_at=datetime.now(UTC) + SYNC_INTERVAL,
        )
        await self.session.commit()
