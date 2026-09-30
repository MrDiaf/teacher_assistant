from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.errors import CalendarReadOnlyError, InvalidIcsError
from app.calendar.ics import ParsedIcsCalendar, ParsedIcsEvent
from app.calendar.models import Calendar, CalendarEvent, CalendarSourceType
from app.calendar.repository import CalendarRepository, EventRepository


@dataclass(frozen=True)
class IcsImportProblem:
    index: int
    uid: str | None
    message: str


@dataclass(frozen=True)
class IcsImportResult:
    calendar: Calendar
    imported_events: list[CalendarEvent]
    duplicate_count: int
    skipped_count: int
    errors: list[IcsImportProblem]


class IcsImportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.calendars = CalendarRepository(session)
        self.events = EventRepository(session)

    async def import_calendar(
        self,
        parsed: ParsedIcsCalendar,
        *,
        destination_calendar_id: uuid.UUID | None,
        calendar_name: str | None,
        calendar_color: str,
        subscription_url: str | None = None,
        subscription_synced_at: datetime | None = None,
        subscription_next_sync_at: datetime | None = None,
    ) -> IcsImportResult:
        importable = [event for event in parsed.events if event.is_importable]
        if not importable:
            raise InvalidIcsError(
                "The ICS file contains no importable events. Review the preview errors."
            )

        if destination_calendar_id is None:
            calendar = await self.calendars.create(
                {
                    "name": (calendar_name or parsed.suggested_calendar_name)[:120],
                    "description": f"Imported from {parsed.file_name}",
                    "color": calendar_color,
                    "is_visible": True,
                    "is_read_only": False,
                    "is_importing": True,
                    "source_type": CalendarSourceType.ICS_IMPORT,
                }
            )
            existing_uids: set[str] = set()
            lock_after_import = True
        else:
            calendar = await self.calendars.get(destination_calendar_id, for_update=True)
            if calendar.is_read_only:
                raise CalendarReadOnlyError()
            existing_uids = await self.events.existing_external_uids(
                calendar.id,
                {event.uid for event in importable if event.uid is not None},
            )
            lock_after_import = False

        imported_events: list[CalendarEvent] = []
        duplicate_count = 0
        imported_uids = set(existing_uids)
        for event in importable:
            if event.uid is not None and event.uid in imported_uids:
                duplicate_count += 1
                continue
            created = await self.events.create(self._event_values(calendar.id, event))
            imported_events.append(created)
            if event.uid is not None:
                imported_uids.add(event.uid)

        errors = [
            IcsImportProblem(
                index=event.index,
                uid=event.uid,
                message="; ".join(
                    issue.message for issue in event.issues if issue.severity == "error"
                ),
            )
            for event in parsed.events
            if not event.is_importable
        ]
        if lock_after_import:
            final_changes: dict[str, object] = {
                "is_read_only": True,
                "is_importing": False,
            }
            if subscription_url is not None:
                final_changes.update(
                    {
                        "subscription_url": subscription_url,
                        "subscription_last_synced_at": subscription_synced_at,
                        "subscription_next_sync_at": subscription_next_sync_at,
                        "subscription_error": None,
                    }
                )
            calendar = await self.calendars.update(calendar.id, final_changes)

        await self.session.commit()
        await self.session.refresh(calendar)
        for event in imported_events:
            await self.session.refresh(event)
        return IcsImportResult(
            calendar=calendar,
            imported_events=imported_events,
            duplicate_count=duplicate_count,
            skipped_count=len(errors),
            errors=errors,
        )

    @staticmethod
    def _event_values(calendar_id: uuid.UUID, event: ParsedIcsEvent) -> dict[str, object]:
        if event.start_at is None or event.end_at is None:
            raise InvalidIcsError("An invalid event reached the import stage.")
        return {
            "calendar_id": calendar_id,
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "external_uid": event.uid,
            "start_at": event.start_at,
            "end_at": event.end_at,
            "all_day": event.all_day,
            "timezone": event.timezone,
            "recurrence_rule": event.recurrence_rule,
            "recurrence_parent_id": None,
            "recurrence_original_start_at": None,
            "status": event.status,
        }
