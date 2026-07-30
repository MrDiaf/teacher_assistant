import uuid
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.courses.models import CourseStatus
from app.courses.schemas import CourseCreate, CourseResponse, CourseUpdate
from app.courses.service import CourseService
from app.database.session import get_session

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(
    session: SessionDependency,
    status: CourseStatus | None = None,
) -> list[CourseResponse]:
    courses = await CourseService(session).list_courses(status)
    return [CourseResponse.model_validate(course) for course in courses]


@router.post("/courses", response_model=CourseResponse, status_code=HTTPStatus.CREATED)
async def create_course(payload: CourseCreate, session: SessionDependency) -> CourseResponse:
    course = await CourseService(session).create_course(payload.model_dump())
    return CourseResponse.model_validate(course)


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(course_id: uuid.UUID, session: SessionDependency) -> CourseResponse:
    course = await CourseService(session).get_course(course_id)
    return CourseResponse.model_validate(course)


@router.patch("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    session: SessionDependency,
) -> CourseResponse:
    course = await CourseService(session).update_course(
        course_id, payload.model_dump(exclude_unset=True)
    )
    return CourseResponse.model_validate(course)


@router.delete("/courses/{course_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_course(course_id: uuid.UUID, session: SessionDependency) -> Response:
    await CourseService(session).delete_course(course_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.post("/courses/{course_id}/archive", response_model=CourseResponse)
async def archive_course(course_id: uuid.UUID, session: SessionDependency) -> CourseResponse:
    course = await CourseService(session).archive_course(course_id)
    return CourseResponse.model_validate(course)


@router.post("/courses/{course_id}/restore", response_model=CourseResponse)
async def restore_course(course_id: uuid.UUID, session: SessionDependency) -> CourseResponse:
    course = await CourseService(session).restore_course(course_id)
    return CourseResponse.model_validate(course)
