import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.ics import ParsedIcsCalendar, parse_ics
from app.calendar.import_schemas import (
    IcsImportErrorResponse,
    IcsImportResponse,
    IcsIssueResponse,
    IcsPreviewEventResponse,
    IcsPreviewResponse,
)
from app.calendar.import_service import IcsImportService
from app.calendar.schemas import HEX_COLOR_PATTERN, CalendarResponse, EventResponse
from app.database.session import get_session

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
IcsBody = Annotated[bytes, Body(media_type="text/calendar")]


def preview_response(parsed: ParsedIcsCalendar) -> IcsPreviewResponse:
    return IcsPreviewResponse(
        file_name=parsed.file_name,
        suggested_calendar_name=parsed.suggested_calendar_name,
        total_events=len(parsed.events),
        importable_events=sum(event.is_importable for event in parsed.events),
        skipped_events=sum(not event.is_importable for event in parsed.events),
        events=[
            IcsPreviewEventResponse(
                index=event.index,
                uid=event.uid,
                title=event.title,
                start_at=event.start_at,
                end_at=event.end_at,
                all_day=event.all_day,
                timezone=event.timezone,
                status=event.status.value,
                recurrence_rule=event.recurrence_rule,
                is_importable=event.is_importable,
                issues=[
                    IcsIssueResponse(severity=issue.severity, message=issue.message)
                    for issue in event.issues
                ],
            )
            for event in parsed.events
        ],
    )


@router.post("/calendar-imports/ics/preview", response_model=IcsPreviewResponse)
async def preview_ics(
    content: IcsBody,
    file_name: Annotated[str, Query(min_length=1, max_length=255)] = "calendar.ics",
) -> IcsPreviewResponse:
    return preview_response(parse_ics(content, file_name))


@router.post("/calendar-imports/ics", response_model=IcsImportResponse)
async def import_ics(
    content: IcsBody,
    session: SessionDependency,
    file_name: Annotated[str, Query(min_length=1, max_length=255)] = "calendar.ics",
    destination_calendar_id: Annotated[uuid.UUID | None, Query()] = None,
    calendar_name: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    calendar_color: Annotated[str, Query(pattern=HEX_COLOR_PATTERN)] = "#5b7fa3",
) -> IcsImportResponse:
    parsed = parse_ics(content, file_name)
    result = await IcsImportService(session).import_calendar(
        parsed,
        destination_calendar_id=destination_calendar_id,
        calendar_name=calendar_name,
        calendar_color=calendar_color,
    )
    return IcsImportResponse(
        calendar=CalendarResponse.model_validate(result.calendar),
        imported_count=len(result.imported_events),
        duplicate_count=result.duplicate_count,
        skipped_count=result.skipped_count,
        errors=[
            IcsImportErrorResponse(index=problem.index, uid=problem.uid, message=problem.message)
            for problem in result.errors
        ],
        imported_events=[EventResponse.model_validate(event) for event in result.imported_events],
        destination_calendar_id=result.calendar.id,
    )
