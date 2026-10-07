"""Sign-in routes and the middleware that requires a session for every API call.

The host installs both in every assembled application (full and focused module
hosts) so no catalog selection can omit the access check.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.access.service import (
    MAX_PASSWORD_LENGTH,
    SESSION_COOKIE_NAME,
    SESSION_LIFETIME,
    attempt_login,
    client_key,
    get_password_record,
    session_token_is_valid,
)
from app.database.session import session_factory

logger = logging.getLogger(__name__)

STATUS_PATH = "/api/v1/access/status"
LOGIN_PATH = "/api/v1/access/login"
_OPEN_PATHS = frozenset({"/health", STATUS_PATH, LOGIN_PATH})
_MAX_LOGIN_BODY_BYTES = 4096

router = APIRouter()


def _access_error(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    # Built directly instead of raising ApplicationError so unauthenticated
    # traffic cannot fill the diagnostics tables.
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "error_id": str(uuid.uuid4()),
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": str(getattr(request.state, "request_id", uuid.uuid4())),
        },
    )


def _request_client_key(request: Request) -> str:
    peer = request.client.host if request.client else None
    return client_key(peer, request.headers.get("x-forwarded-for"))


def _is_https(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    return forwarded_proto.lower() == "https" or request.url.scheme == "https"


async def _read_login_password(request: Request) -> str | None:
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > _MAX_LOGIN_BODY_BYTES:
            return None
    try:
        payload = json.loads(body)
    except ValueError:
        return None
    password = payload.get("password") if isinstance(payload, dict) else None
    if not isinstance(password, str) or not 1 <= len(password) <= MAX_PASSWORD_LENGTH:
        return None
    return password


@router.get(STATUS_PATH, tags=["access"])
async def access_status(request: Request) -> dict[str, bool]:
    async with session_factory() as session:
        record = await get_password_record(session)
    if record is None:
        return {"password_required": False, "authenticated": True}
    token = request.cookies.get(SESSION_COOKIE_NAME)
    authenticated = session_token_is_valid(token, record.session_secret, datetime.now(UTC))
    return {"password_required": True, "authenticated": authenticated}


@router.post(LOGIN_PATH, tags=["access"])
async def access_login(request: Request) -> Response:
    password = await _read_login_password(request)
    if password is None:
        return _access_error(
            request, 422, "request_validation_error", "Enter the password to sign in."
        )
    async with session_factory() as session:
        record = await get_password_record(session)
        if record is None:
            return JSONResponse({"password_required": False, "authenticated": True})
        key = _request_client_key(request)
        result = await attempt_login(session, record, key, password, datetime.now(UTC))

    if result.token is not None:
        response = JSONResponse({"password_required": True, "authenticated": True})
        response.set_cookie(
            SESSION_COOKIE_NAME,
            result.token,
            max_age=int(SESSION_LIFETIME.total_seconds()),
            httponly=True,
            samesite="lax",
            secure=_is_https(request),
            path="/",
        )
        return response
    if result.retry_after_seconds is not None:
        logger.warning("Owner sign-in cooldown active for client %s", key)
        minutes = -(-result.retry_after_seconds // 60)
        return _access_error(
            request,
            429,
            "access_cooldown",
            f"Too many incorrect passwords. Try again in {minutes} minute"
            f"{'' if minutes == 1 else 's'}.",
            {"retry_after_seconds": result.retry_after_seconds},
            {"Retry-After": str(result.retry_after_seconds)},
        )
    return _access_error(
        request,
        401,
        "access_password_incorrect",
        "Incorrect password.",
        {"attempts_before_cooldown": result.attempts_before_cooldown},
    )


async def require_owner_access(request: Request, call_next):
    if request.url.path in _OPEN_PATHS:
        return await call_next(request)
    try:
        async with session_factory() as session:
            record = await get_password_record(session)
    except Exception:
        logger.error("Owner access check failed; refusing the request.")
        return _access_error(
            request, 503, "access_unavailable", "Sign-in is temporarily unavailable."
        )
    if record is not None and not session_token_is_valid(
        request.cookies.get(SESSION_COOKIE_NAME), record.session_secret, datetime.now(UTC)
    ):
        return _access_error(
            request, 401, "access_required", "Sign in to Teacher Assistant to continue."
        )
    return await call_next(request)
