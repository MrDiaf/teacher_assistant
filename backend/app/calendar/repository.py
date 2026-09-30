from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, delete, or_, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.errors import (
    CalendarNotFoundError,
    CalendarReadOnlyError,
    CalendarSourceProtectedError,
    DuplicateExternalUidError,
    EventNotFoundError,
    IcsSubscriptionNotFoundError,
    InvalidRecurrenceParentError,
)
from app.calendar.models import Calendar, CalendarEvent, CalendarSourceType

READ_ONLY_CALENDAR_FIELDS = {"name", "description", "color"}


def _translate_database_protection(exc: DBAPIError) -> None:
    database_message = str(exc.orig)
    if "calendar_read_only" in database_message:
        raise CalendarReadOnlyError() from exc
    if "calendar_source_protected" in database_message:
        raise CalendarSourceProtectedError() from exc
    if "uq_events_calendar_external_uid" in database_message:
        raise DuplicateExternalUidError() from exc


class CalendarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> list[Calendar]:
        statement = select(Calendar).order_by(Calendar.created_at, Calendar.name)
        result = await self.session.scalars(statement)
        return list(result)

    async def list_due_subscriptions(self, due_at: datetime) -> list[Calendar]:
        statement = (
            select(Calendar)
            .where(
                Calendar.subscription_url.is_not(None),
                Calendar.subscription_next_sync_at <= due_at,
            )
            .order_by(Calendar.subscription_next_sync_at)
        )
        return list(await self.session.scalars(statement))

    async def get(self, calendar_id: uuid.UUID, *, for_update: bool = False) -> Calendar:
        statement = select(Calendar).where(Calendar.id == calendar_id)
        if for_update:
            statement = statement.with_for_update()
        calendar = await self.session.scalar(statement)
        if calendar is None:
            raise CalendarNotFoundError()
        return calendar

    async def create(self, values: dict[str, Any]) -> Calendar:
        calendar = Calendar(**values)
        self.session.add(calendar)
        try:
            await self.session.flush()
        except DBAPIError as exc:
            _translate_database_protection(exc)
            raise
        return calendar

    async def update(self, calendar_id: uuid.UUID, changes: dict[str, Any]) -> Calendar:
        calendar = await self.get(calendar_id, for_update=True)
        self._ensure_update_allowed(calendar, changes)
        for field, value in changes.items():
            setattr(calendar, field, value)
        try:
            await self.session.flush()
        except DBAPIError as exc:
            _translate_database_protection(exc)
            raise
        return calendar

    async def delete(self, calendar_id: uuid.UUID) -> None:
        calendar = await self.get(calendar_id, for_update=True)
        if calendar.is_read_only:
            raise CalendarReadOnlyError()
        if calendar.source_type != CalendarSourceType.LOCAL:
            raise CalendarSourceProtectedError()
        await self.session.delete(calendar)
        try:
            await self.session.flush()
        except DBAPIError as exc:
            _translate_database_protection(exc)
            raise

    async def begin_subscription_sync(self, calendar_id: uuid.UUID) -> Calendar:
        calendar = await self.get(calendar_id, for_update=True)
        if (
            not calendar.is_subscribed
            or not calendar.is_read_only
            or calendar.source_type != CalendarSourceType.ICS_IMPORT
        ):
            raise IcsSubscriptionNotFoundError()
        calendar.is_importing = True
        await self.session.flush()
        return calendar

    async def finish_subscription_sync(
        self,
        calendar: Calendar,
        *,
        synced_at: datetime,
        next_sync_at: datetime,
    ) -> Calendar:
        calendar.is_importing = False
        calendar.subscription_last_synced_at = synced_at
        calendar.subscription_next_sync_at = next_sync_at
        calendar.subscription_error = None
        await self.session.flush()
        return calendar

    async def record_subscription_failure(
        self,
        calendar_id: uuid.UUID,
        *,
        message: str,
        next_sync_at: datetime,
    ) -> Calendar:
        calendar = await self.get(calendar_id, for_update=True)
        if not calendar.is_subscribed:
            raise IcsSubscriptionNotFoundError()
        calendar.subscription_error = message[:500]
        calendar.subscription_next_sync_at = next_sync_at
        await self.session.flush()
        return calendar

    @staticmethod
    def _ensure_update_allowed(calendar: Calendar, changes: dict[str, Any]) -> None:
        if (
            changes.get("is_read_only") is False
            and calendar.source_type != CalendarSourceType.LOCAL
        ):
            raise CalendarSourceProtectedError()
        if calendar.is_read_only and READ_ONLY_CALENDAR_FIELDS.intersection(changes):
            raise CalendarReadOnlyError()


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        calendar_id: uuid.UUID | None = None,
        calendar_ids: set[uuid.UUID] | None = None,
        starts_before: datetime | None = None,
        ends_after: datetime | None = None,
        limit: int | None = None,
    ) -> list[CalendarEvent]:
        statement: Select[tuple[CalendarEvent]] = select(CalendarEvent).order_by(
            CalendarEvent.start_at, CalendarEvent.id
        )
        if calendar_id is not None:
            statement = statement.where(CalendarEvent.calendar_id == calendar_id)
        if calendar_ids is not None:
            statement = statement.where(CalendarEvent.calendar_id.in_(calendar_ids))
        range_conditions = []
        if starts_before is not None:
            range_conditions.append(CalendarEvent.start_at < starts_before)
        if ends_after is not None:
            range_conditions.append(CalendarEvent.end_at > ends_after)
        if range_conditions:
            statement = statement.where(
                or_(
                    and_(*range_conditions),
                    CalendarEvent.recurrence_rule.is_not(None),
                    CalendarEvent.recurrence_parent_id.is_not(None),
                )
            )
        if limit is not None:
            statement = statement.limit(limit)
        return list(await self.session.scalars(statement))

    async def get(self, event_id: uuid.UUID, *, for_update: bool = False) -> CalendarEvent:
        statement = select(CalendarEvent).where(CalendarEvent.id == event_id)
        if for_update:
            statement = statement.with_for_update()
        event = await self.session.scalar(statement)
        if event is None:
            raise EventNotFoundError()
        return event

    async def existing_external_uids(
        self, calendar_id: uuid.UUID, external_uids: set[str]
    ) -> set[str]:
        if not external_uids:
            return set()
        statement = select(CalendarEvent.external_uid).where(
            CalendarEvent.calendar_id == calendar_id,
            CalendarEvent.external_uid.in_(external_uids),
        )
        return set(await self.session.scalars(statement))

    async def list_subscription_events(self, calendar_id: uuid.UUID) -> list[CalendarEvent]:
        await self._get_syncing_subscription(calendar_id)
        statement = select(CalendarEvent).where(CalendarEvent.calendar_id == calendar_id)
        return list(await self.session.scalars(statement))

    async def sync_create(self, values: dict[str, Any]) -> CalendarEvent:
        await self._get_syncing_subscription(values["calendar_id"])
        event = CalendarEvent(**values)
        self.session.add(event)
        await self._flush_with_protection()
        return event

    async def sync_update(self, event: CalendarEvent, changes: dict[str, Any]) -> CalendarEvent:
        await self._get_syncing_subscription(event.calendar_id)
        for field, value in changes.items():
            setattr(event, field, value)
        await self._flush_with_protection()
        return event

    async def sync_delete(self, event: CalendarEvent) -> None:
        await self._get_syncing_subscription(event.calendar_id)
        await self.session.delete(event)
        await self._flush_with_protection()

    async def create(self, values: dict[str, Any]) -> CalendarEvent:
        calendar = await self._get_writable_calendar(values["calendar_id"])
        await self._validate_recurrence_parent(
            values.get("recurrence_parent_id"), calendar.id, event_id=None
        )
        event = CalendarEvent(**values)
        self.session.add(event)
        await self._flush_with_protection()
        return event

    async def update(self, event_id: uuid.UUID, changes: dict[str, Any]) -> CalendarEvent:
        event = await self.get(event_id, for_update=True)
        await self._get_writable_calendar(event.calendar_id)
        target_calendar_id = changes.get("calendar_id", event.calendar_id)
        if target_calendar_id != event.calendar_id:
            await self._get_writable_calendar(target_calendar_id)
        recurrence_parent_id = changes.get("recurrence_parent_id", event.recurrence_parent_id)
        await self._validate_recurrence_parent(
            recurrence_parent_id, target_calendar_id, event_id=event.id
        )
        for field, value in changes.items():
            setattr(event, field, value)
        await self._flush_with_protection()
        return event

    async def delete(self, event_id: uuid.UUID) -> None:
        event = await self.get(event_id, for_update=True)
        await self._get_writable_calendar(event.calendar_id)
        await self.session.delete(event)
        await self._flush_with_protection()

    async def get_exception(
        self,
        recurrence_parent_id: uuid.UUID,
        recurrence_original_start_at: datetime,
        *,
        for_update: bool = False,
    ) -> CalendarEvent | None:
        statement = select(CalendarEvent).where(
            CalendarEvent.recurrence_parent_id == recurrence_parent_id,
            CalendarEvent.recurrence_original_start_at == recurrence_original_start_at,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def list_exceptions(self, recurrence_parent_id: uuid.UUID) -> list[CalendarEvent]:
        statement = select(CalendarEvent).where(
            CalendarEvent.recurrence_parent_id == recurrence_parent_id
        )
        return list(await self.session.scalars(statement))

    async def delete_series(self, recurrence_parent_id: uuid.UUID) -> None:
        parent = await self.get(recurrence_parent_id, for_update=True)
        await self._get_writable_calendar(parent.calendar_id)
        await self.session.execute(
            delete(CalendarEvent).where(CalendarEvent.recurrence_parent_id == recurrence_parent_id)
        )
        await self.session.delete(parent)
        await self._flush_with_protection()

    async def delete_exceptions(self, recurrence_parent_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(CalendarEvent).where(CalendarEvent.recurrence_parent_id == recurrence_parent_id)
        )

    async def _get_writable_calendar(self, calendar_id: uuid.UUID) -> Calendar:
        calendar = await self.session.scalar(
            select(Calendar).where(Calendar.id == calendar_id).with_for_update()
        )
        if calendar is None:
            raise CalendarNotFoundError()
        if calendar.is_read_only:
            raise CalendarReadOnlyError()
        return calendar

    async def _get_syncing_subscription(self, calendar_id: uuid.UUID) -> Calendar:
        calendar = await self.session.scalar(
            select(Calendar).where(Calendar.id == calendar_id).with_for_update()
        )
        if (
            calendar is None
            or not calendar.is_read_only
            or not calendar.is_importing
            or not calendar.is_subscribed
            or calendar.source_type != CalendarSourceType.ICS_IMPORT
        ):
            raise CalendarReadOnlyError()
        return calendar

    async def _validate_recurrence_parent(
        self,
        recurrence_parent_id: uuid.UUID | None,
        calendar_id: uuid.UUID,
        *,
        event_id: uuid.UUID | None,
    ) -> None:
        if recurrence_parent_id is None:
            return
        parent = await self.session.scalar(
            select(CalendarEvent).where(CalendarEvent.id == recurrence_parent_id)
        )
        if parent is None or parent.calendar_id != calendar_id or parent.id == event_id:
            raise InvalidRecurrenceParentError()

    async def _flush_with_protection(self) -> None:
        try:
            await self.session.flush()
        except DBAPIError as exc:
            _translate_database_protection(exc)
            raise
