import uuid
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.documents.schemas import (
    DocumentProjectCreate,
    DocumentProjectResponse,
    DocumentProjectUpdate,
    DocumentTagCreate,
    DocumentTagResponse,
    DocumentTagUpdate,
)
from app.documents.service import DocumentService

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/document-projects", response_model=list[DocumentProjectResponse])
async def list_projects(
    session: SessionDependency,
    search: Annotated[str | None, Query(max_length=200)] = None,
    tag_id: uuid.UUID | None = None,
) -> list[DocumentProjectResponse]:
    normalized_search = search.strip() if search else None
    projects = await DocumentService(session).list_projects(normalized_search, tag_id)
    return [DocumentProjectResponse.model_validate(project) for project in projects]


@router.post(
    "/document-projects",
    response_model=DocumentProjectResponse,
    status_code=HTTPStatus.CREATED,
)
async def create_project(
    payload: DocumentProjectCreate, session: SessionDependency
) -> DocumentProjectResponse:
    project = await DocumentService(session).create_project(payload.title)
    return DocumentProjectResponse.model_validate(project)


@router.get("/document-projects/{project_id}", response_model=DocumentProjectResponse)
async def get_project(project_id: uuid.UUID, session: SessionDependency) -> DocumentProjectResponse:
    project = await DocumentService(session).get_project(project_id)
    return DocumentProjectResponse.model_validate(project)


@router.patch("/document-projects/{project_id}", response_model=DocumentProjectResponse)
async def rename_project(
    project_id: uuid.UUID,
    payload: DocumentProjectUpdate,
    session: SessionDependency,
) -> DocumentProjectResponse:
    project = await DocumentService(session).rename_project(project_id, payload.title or "")
    return DocumentProjectResponse.model_validate(project)


@router.delete("/document-projects/{project_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_project(project_id: uuid.UUID, session: SessionDependency) -> Response:
    await DocumentService(session).delete_project(project_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.get("/document-projects/{project_id}/main.tex")
async def download_main_tex(project_id: uuid.UUID, session: SessionDependency) -> Response:
    content = await DocumentService(session).main_tex(project_id)
    return Response(
        content=content,
        media_type="application/x-tex",
        headers={
            "Content-Disposition": 'attachment; filename="main.tex"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/document-projects/{project_id}/source.zip")
async def download_source_zip(project_id: uuid.UUID, session: SessionDependency) -> Response:
    content = await DocumentService(session).source_zip(project_id)
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{project_id}-source.zip"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/document-tags", response_model=list[DocumentTagResponse])
async def list_tags(session: SessionDependency) -> list[DocumentTagResponse]:
    tags = await DocumentService(session).list_tags()
    return [DocumentTagResponse.model_validate(tag) for tag in tags]


@router.post("/document-tags", response_model=DocumentTagResponse, status_code=HTTPStatus.CREATED)
async def create_tag(payload: DocumentTagCreate, session: SessionDependency) -> DocumentTagResponse:
    tag = await DocumentService(session).create_tag(payload.model_dump())
    return DocumentTagResponse.model_validate(tag)


@router.patch("/document-tags/{tag_id}", response_model=DocumentTagResponse)
async def update_tag(
    tag_id: uuid.UUID, payload: DocumentTagUpdate, session: SessionDependency
) -> DocumentTagResponse:
    tag = await DocumentService(session).update_tag(tag_id, payload.model_dump(exclude_unset=True))
    return DocumentTagResponse.model_validate(tag)


@router.delete("/document-tags/{tag_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_tag(tag_id: uuid.UUID, session: SessionDependency) -> Response:
    await DocumentService(session).delete_tag(tag_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.put(
    "/document-projects/{project_id}/tags/{tag_id}",
    response_model=DocumentProjectResponse,
)
async def assign_tag(
    project_id: uuid.UUID, tag_id: uuid.UUID, session: SessionDependency
) -> DocumentProjectResponse:
    project = await DocumentService(session).assign_tag(project_id, tag_id)
    return DocumentProjectResponse.model_validate(project)


@router.delete(
    "/document-projects/{project_id}/tags/{tag_id}",
    response_model=DocumentProjectResponse,
)
async def unassign_tag(
    project_id: uuid.UUID, tag_id: uuid.UUID, session: SessionDependency
) -> DocumentProjectResponse:
    project = await DocumentService(session).unassign_tag(project_id, tag_id)
    return DocumentProjectResponse.model_validate(project)
