import uuid
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.course_sources.models import CourseSourceType
from app.course_sources.schemas import CourseSourceResponse
from app.course_sources.service import CourseSourceService
from app.database.session import get_session

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/courses/{course_id}/sources",
    response_model=list[CourseSourceResponse],
)
async def list_course_sources(
    course_id: uuid.UUID,
    session: SessionDependency,
    source_type: CourseSourceType | None = None,
) -> list[CourseSourceResponse]:
    sources = await CourseSourceService(session).list_sources(course_id, source_type)
    return [CourseSourceResponse.model_validate(source) for source in sources]


@router.post(
    "/courses/{course_id}/sources",
    response_model=CourseSourceResponse,
    status_code=HTTPStatus.CREATED,
)
async def upload_course_source(
    course_id: uuid.UUID,
    request: Request,
    session: SessionDependency,
    source_type: Annotated[CourseSourceType, Query()],
    file_name: Annotated[str, Query(min_length=1, max_length=255)],
    display_name: Annotated[str | None, Query(min_length=1, max_length=240)] = None,
) -> CourseSourceResponse:
    raw_content_length = request.headers.get("content-length")
    try:
        content_length = int(raw_content_length) if raw_content_length else None
    except ValueError:
        content_length = None
    source = await CourseSourceService(session).upload_source(
        course_id=course_id,
        source_type=source_type,
        file_name=file_name,
        display_name=display_name,
        chunks=request.stream(),
        content_length=content_length,
    )
    return CourseSourceResponse.model_validate(source)


@router.get(
    "/course-sources/{source_id}",
    response_model=CourseSourceResponse,
)
async def get_course_source(
    source_id: uuid.UUID,
    session: SessionDependency,
) -> CourseSourceResponse:
    source = await CourseSourceService(session).get_source(source_id)
    return CourseSourceResponse.model_validate(source)


@router.api_route(
    "/course-sources/{source_id}/content",
    methods=["GET", "HEAD"],
    response_class=FileResponse,
)
async def get_course_source_content(
    source_id: uuid.UUID,
    session: SessionDependency,
) -> FileResponse:
    content = await CourseSourceService(session).get_pdf_content(source_id)
    return FileResponse(
        content.resolved_file.path,
        filename=content.original_filename,
        media_type="application/pdf",
        content_disposition_type="inline",
        stat_result=content.resolved_file.stat_result,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Cross-Origin-Resource-Policy": "same-origin",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete(
    "/course-sources/{source_id}",
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_course_source(
    source_id: uuid.UUID,
    session: SessionDependency,
) -> Response:
    await CourseSourceService(session).delete_source(source_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.post(
    "/course-sources/{source_id}/extract",
    response_model=CourseSourceResponse,
)
async def extract_course_source(
    source_id: uuid.UUID,
    session: SessionDependency,
) -> CourseSourceResponse:
    source = await CourseSourceService(session).extract_source(source_id)
    return CourseSourceResponse.model_validate(source)


@router.post(
    "/course-sources/{source_id}/retry-extraction",
    response_model=CourseSourceResponse,
)
async def retry_course_source_extraction(
    source_id: uuid.UUID,
    session: SessionDependency,
) -> CourseSourceResponse:
    source = await CourseSourceService(session).retry_extraction(source_id)
    return CourseSourceResponse.model_validate(source)
