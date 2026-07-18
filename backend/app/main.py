from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.calendar.routes import router as calendar_router
from app.core.errors import ApplicationError
from app.database.session import session_factory

app = FastAPI(title="Teacher Assistant API", version="1.0.0")
app.include_router(calendar_router, prefix="/api/v1", tags=["calendar"])


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
