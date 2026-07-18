import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.calendar.import_routes import preview_response
from app.calendar.import_schemas import (
    IcsImportErrorResponse,
    IcsImportResponse,
    IcsPreviewResponse,
    IcsSubscriptionCreateRequest,
    IcsSubscriptionPreviewRequest,
    IcsSubscriptionSyncResponse,
)
from app.calendar.schemas import CalendarResponse, EventResponse
from app.calendar.subscription_service import IcsSubscriptionService
from app.database.session import get_session

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post("/calendar-subscriptions/ics/preview", response_model=IcsPreviewResponse)
async def preview_ics_subscription(
    payload: IcsSubscriptionPreviewRequest,
    session: SessionDependency,
) -> IcsPreviewResponse:
    return preview_response(await IcsSubscriptionService(session).preview(payload.url))


@router.post("/calendar-subscriptions/ics", response_model=IcsImportResponse)
async def create_ics_subscription(
    payload: IcsSubscriptionCreateRequest,
    session: SessionDependency,
) -> IcsImportResponse:
    result = await IcsSubscriptionService(session).create(
        payload.url,
        calendar_name=payload.calendar_name,
        calendar_color=payload.calendar_color,
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


@router.post(
    "/calendar-subscriptions/ics/{calendar_id}/sync",
    response_model=IcsSubscriptionSyncResponse,
)
async def sync_ics_subscription(
    calendar_id: uuid.UUID,
    session: SessionDependency,
) -> IcsSubscriptionSyncResponse:
    result = await IcsSubscriptionService(session).sync(calendar_id)
    return IcsSubscriptionSyncResponse(
        calendar=CalendarResponse.model_validate(result.calendar),
        created_count=result.created_count,
        updated_count=result.updated_count,
        deleted_count=result.deleted_count,
        skipped_count=result.skipped_count,
    )
