"""Owner password, sign-in sessions, and per-address brute-force cooldowns.

Access control is off until `make password` stores a password. After that,
every API request needs a signed session cookie. Failed sign-ins are counted per
client address; every fifth failure starts a cooldown that doubles each time
(1, 2, 4, ... minutes, capped at one day). Setting a password clears every
cooldown and signs out every existing session.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.access.models import AccessLoginThrottle, AccessPassword
from app.core.config import get_settings

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 1024
FAILURES_PER_COOLDOWN = 5
BASE_COOLDOWN_SECONDS = 60
MAX_COOLDOWN_SECONDS = 24 * 60 * 60
SESSION_LIFETIME = timedelta(days=30)
SESSION_COOKIE_NAME = "teacher_assistant_access"

_SCRYPT_N = 2**15
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024


def validate_new_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"The password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"The password must be at most {MAX_PASSWORD_LENGTH} characters.")
    if not password.strip():
        raise ValueError("The password cannot be only whitespace.")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, maxmem=_SCRYPT_MAXMEM
    )
    encode = base64.b64encode
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${encode(salt).decode()}${encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = encoded.split("$")
        if scheme != "scrypt":
            return False
        expected_bytes = base64.b64decode(expected)
        digest = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            maxmem=_SCRYPT_MAXMEM,
            dklen=len(expected_bytes),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected_bytes)


def cooldown_seconds(failed_attempts: int) -> int | None:
    """Cooldown started by this failure count, or None when no cooldown starts."""
    if failed_attempts <= 0 or failed_attempts % FAILURES_PER_COOLDOWN:
        return None
    exponent = min(failed_attempts // FAILURES_PER_COOLDOWN - 1, 20)
    return min(BASE_COOLDOWN_SECONDS * 2**exponent, MAX_COOLDOWN_SECONDS)


def create_session_token(session_secret: str, now: datetime) -> str:
    expires = int((now + SESSION_LIFETIME).timestamp())
    return f"{expires}.{_sign(session_secret, expires)}"


def session_token_is_valid(token: str | None, session_secret: str, now: datetime) -> bool:
    if not token or len(token) > 200:
        return False
    expires_text, _, signature = token.partition(".")
    if not expires_text.isdigit():
        return False
    expires = int(expires_text)
    if expires <= now.timestamp():
        return False
    return hmac.compare_digest(signature, _sign(session_secret, expires))


def _sign(session_secret: str, expires: int) -> str:
    return hmac.new(session_secret.encode(), str(expires).encode(), hashlib.sha256).hexdigest()


@lru_cache
def _trusted_proxy_networks(
    configured: str,
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return tuple(
        ipaddress.ip_network(item.strip(), strict=False)
        for item in configured.split(",")
        if item.strip()
    )


def _parse_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def client_key(peer: str | None, forwarded_for: str | None) -> str:
    """Return the cooldown bucket for a request.

    Walk `X-Forwarded-For` from the right, starting at the socket peer, and
    skip only configured trusted proxies (loopback and the Docker network by
    default: Vite and the host-side Docker gateway that Tailscale Funnel reaches
    through). The first untrusted address is the client. Tailscale replaces any
    client-supplied `X-Forwarded-For`, and a LAN client's address is its own
    socket peer, so neither can choose its bucket. IPv6 clients are bucketed by
    /64 because one subscriber normally controls a whole /64.
    """
    trusted = _trusted_proxy_networks(get_settings().access_trusted_proxy_networks)
    hops = [hop for hop in (forwarded_for or "").split(",") if hop.strip()][-20:]
    address = _parse_address(peer or "")
    if address is None:
        return "unknown"
    while hops and any(address in network for network in trusted):
        previous = _parse_address(hops.pop())
        if previous is None:
            break
        address = previous
    if isinstance(address, ipaddress.IPv6Address):
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)


async def get_password_record(session: AsyncSession) -> AccessPassword | None:
    return await session.get(AccessPassword, 1)


async def set_password(session: AsyncSession, password: str) -> None:
    """Store a new owner password, sign out every session, and clear all cooldowns."""
    validate_new_password(password)
    password_hash = await asyncio.to_thread(hash_password, password)
    session_secret = secrets.token_hex(32)
    await session.execute(
        insert(AccessPassword)
        .values(id=1, password_hash=password_hash, session_secret=session_secret)
        .on_conflict_do_update(
            index_elements=[AccessPassword.id],
            set_={
                "password_hash": password_hash,
                "session_secret": session_secret,
                "updated_at": datetime.now(UTC),
            },
        )
    )
    await session.execute(delete(AccessLoginThrottle))
    await session.commit()


@dataclass(frozen=True)
class LoginResult:
    token: str | None = None
    retry_after_seconds: int | None = None
    attempts_before_cooldown: int | None = None


async def attempt_login(
    session: AsyncSession,
    record: AccessPassword,
    key: str,
    password: str,
    now: datetime,
) -> LoginResult:
    """Check one password guess for one client address.

    The address's throttle row stays locked while the password is checked, so
    parallel guesses from one address are counted one at a time and cannot slip
    past the cooldown. A locked address gets no password check at all.
    """
    await session.execute(
        insert(AccessLoginThrottle)
        .values(client_key=key, failed_attempts=0)
        .on_conflict_do_nothing(index_elements=[AccessLoginThrottle.client_key])
    )
    throttle = await session.scalar(
        select(AccessLoginThrottle)
        .where(AccessLoginThrottle.client_key == key)
        .with_for_update()
    )
    if throttle is None:  # removed by a concurrent password change
        await session.rollback()
        return LoginResult(retry_after_seconds=1)

    if throttle.locked_until is not None and throttle.locked_until > now:
        await session.commit()
        remaining = (throttle.locked_until - now).total_seconds()
        return LoginResult(retry_after_seconds=max(1, int(remaining + 0.999)))

    if await asyncio.to_thread(verify_password, password, record.password_hash):
        await session.delete(throttle)
        await session.commit()
        return LoginResult(token=create_session_token(record.session_secret, now))

    throttle.failed_attempts += 1
    cooldown = cooldown_seconds(throttle.failed_attempts)
    if cooldown is not None:
        throttle.locked_until = now + timedelta(seconds=cooldown)
    await session.commit()
    if cooldown is not None:
        return LoginResult(retry_after_seconds=cooldown)
    return LoginResult(
        attempts_before_cooldown=FAILURES_PER_COOLDOWN
        - throttle.failed_attempts % FAILURES_PER_COOLDOWN
    )
