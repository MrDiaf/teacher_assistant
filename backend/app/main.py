import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.ai.routes import router as ai_router
from app.assistant.routes import router as assistant_router
from app.calendar.import_routes import router as calendar_import_router
from app.calendar.routes import router as calendar_router
from app.calendar.subscription_routes import router as calendar_subscription_router
from app.calendar.subscription_scheduler import subscription_scheduler
from app.codex_runtime.adapter import get_codex_auth_manager
from app.core.errors import ApplicationError
from app.course_calendars.routes import router as course_calendar_router
from app.course_sources.routes import router as course_source_router
from app.courses.routes import router as course_router
from app.database.session import session_factory
from app.diagnostics.redaction import redact_text
from app.diagnostics.routes import router as diagnostic_router
from app.diagnostics.service import DiagnosticService
from app.notes.routes import router as note_router
from app.notes.summary_routes import router as note_summary_router

logger = logging.getLogger(__name__)


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
app.include_router(ai_router, prefix="/api/v1", tags=["ai"])
app.include_router(calendar_router, prefix="/api/v1", tags=["calendar"])
app.include_router(course_router, prefix="/api/v1", tags=["courses"])
app.include_router(
    course_calendar_router,
    prefix="/api/v1",
    tags=["course-calendars"],
)
app.include_router(course_source_router, prefix="/api/v1", tags=["course-materials"])
app.include_router(note_router, prefix="/api/v1", tags=["course-notes"])
app.include_router(
    note_summary_router,
    prefix="/api/v1",
    tags=["course-note-summaries"],
)
app.include_router(assistant_router, prefix="/api/v1", tags=["assistant"])
app.include_router(diagnostic_router, prefix="/api/v1", tags=["diagnostics"])
app.include_router(calendar_import_router, prefix="/api/v1", tags=["calendar-import"])
app.include_router(
    calendar_subscription_router,
    prefix="/api/v1",
    tags=["calendar-subscription"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request.state.request_id = uuid.uuid4()
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(request.state.request_id)
    return response


def _operation_name(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched_route")
    return f"{request.method} {path}"


def _safe_request_details(request: Request) -> dict:
    details: dict[str, str | int] = {}
    content_type = request.headers.get("content-type")
    if content_type:
        details["content_type"] = content_type.split(";", 1)[0][:160]
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            parsed_length = int(content_length)
            if parsed_length > 0:
                details["content_size"] = parsed_length
        except ValueError:
            pass
    return details


async def _record_safe_error(
    request: Request,
    *,
    code: str,
    message: str,
    details: dict,
    exception_type: str | None,
):
    request_id = getattr(request.state, "request_id", uuid.uuid4())
    try:
        async with session_factory() as session:
            return await DiagnosticService(session).record_error(
                request_id=request_id,
                code=code,
                message=message,
                operation=_operation_name(request),
                details=details,
                exception_type=exception_type,
            )
    except Exception:
        return None


@app.exception_handler(ApplicationError)
async def handle_application_error(request: Request, error: ApplicationError) -> JSONResponse:
    report = await _record_safe_error(
        request,
        code=error.code,
        message=error.message,
        details={
            "status_code": int(error.status_code),
            **_safe_request_details(request),
            **error.details,
        },
        exception_type=type(error).__name__,
    )
    request_id = getattr(request.state, "request_id", uuid.uuid4())
    safe_message = report.message if report is not None else redact_text(error.message)
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error_id": str(report.id) if report is not None else str(uuid.uuid4()),
            "code": error.code,
            "message": safe_message,
            "details": report.details if report is not None else {},
            "request_id": str(request_id),
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    field_errors = [
        {
            "field": ".".join(str(item) for item in entry.get("loc", ())),
            "message": str(entry.get("msg", "Invalid value.")),
            "type": str(entry.get("type", "validation_error")),
        }
        for entry in error.errors()
    ]
    report = await _record_safe_error(
        request,
        code="request_validation_error",
        message="The request contains invalid input.",
        details={
            **_safe_request_details(request),
            "field_errors": field_errors,
        },
        exception_type=type(error).__name__,
    )
    request_id = getattr(request.state, "request_id", uuid.uuid4())
    return JSONResponse(
        status_code=422,
        content={
            "error_id": str(report.id) if report is not None else str(uuid.uuid4()),
            "code": "request_validation_error",
            "message": "The request contains invalid input.",
            "details": report.details if report is not None else {"field_errors": field_errors},
            "request_id": str(request_id),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(
    request: Request,
    error: StarletteHTTPException,
) -> JSONResponse:
    message = (
        error.detail
        if isinstance(error.detail, str)
        else "The request could not be completed."
    )
    code = "route_not_found" if error.status_code == 404 else "http_error"
    report = await _record_safe_error(
        request,
        code=code,
        message=message,
        details={
            "status_code": error.status_code,
            **_safe_request_details(request),
        },
        exception_type=type(error).__name__,
    )
    request_id = getattr(request.state, "request_id", uuid.uuid4())
    safe_message = report.message if report is not None else redact_text(message)
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error_id": str(report.id) if report is not None else str(uuid.uuid4()),
            "code": code,
            "message": safe_message,
            "details": report.details if report is not None else {},
            "request_id": str(request_id),
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(
    request: Request,
    error: Exception,
) -> JSONResponse:
    logger.error(
        "Unexpected API failure: request_id=%s error_type=%s",
        getattr(request.state, "request_id", "unknown"),
        type(error).__name__,
    )
    message = "The request failed safely because of an internal application error."
    report = await _record_safe_error(
        request,
        code="internal_error",
        message=message,
        details={
            "status_code": 500,
            **_safe_request_details(request),
        },
        exception_type=type(error).__name__,
    )
    request_id = getattr(request.state, "request_id", uuid.uuid4())
    return JSONResponse(
        status_code=500,
        content={
            "error_id": str(report.id) if report is not None else str(uuid.uuid4()),
            "code": "internal_error",
            "message": message,
            "details": report.details if report is not None else {},
            "request_id": str(request_id),
        },
    )


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    async with session_factory() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}
