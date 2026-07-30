import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.assistant.routes import router as assistant_router
from app.calendar.import_routes import router as calendar_import_router
from app.calendar.routes import router as calendar_router
from app.calendar.subscription_routes import router as calendar_subscription_router
from app.calendar.subscription_scheduler import subscription_scheduler
from app.codex_runtime.adapter import get_codex_auth_manager
from app.core.errors import ApplicationError
from app.course_sources.routes import router as course_source_router
from app.courses.routes import router as course_router
from app.database.session import session_factory
from app.notes.routes import router as note_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    stop = asyncio.Event()
    task = asyncio.create_task(subscription_scheduler(stop))
    try:
        yield
    finally:
        stop.set()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await get_codex_auth_manager().shutdown()


app = FastAPI(title="Teacher Assistant API", version="1.0.0", lifespan=lifespan)
app.include_router(calendar_router, prefix="/api/v1", tags=["calendar"])
app.include_router(course_router, prefix="/api/v1", tags=["courses"])
app.include_router(course_source_router, prefix="/api/v1", tags=["course-materials"])
app.include_router(note_router, prefix="/api/v1", tags=["course-notes"])
app.include_router(assistant_router, prefix="/api/v1", tags=["assistant"])
app.include_router(calendar_import_router, prefix="/api/v1", tags=["calendar-import"])
app.include_router(
    calendar_subscription_router,
    prefix="/api/v1",
    tags=["calendar-subscription"],
)


@app.exception_handler(ApplicationError)
async def handle_application_error(_request: Request, error: ApplicationError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"code": error.code, "message": error.message},
    )


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    async with session_factory() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}
