from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

from app.calendar.errors import (
    IcsFileTooLargeError,
    IcsSubscriptionFetchError,
    InvalidIcsSubscriptionUrlError,
)
from app.calendar.ics import MAX_ICS_BYTES

FETCH_TIMEOUT_SECONDS = 15.0


def _is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return ip.is_global


async def validate_subscription_url(url: str) -> str:
    value = url.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise InvalidIcsSubscriptionUrlError()
    if parsed.username is not None or parsed.password is not None:
        raise InvalidIcsSubscriptionUrlError("Subscription URLs cannot contain user credentials.")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise InvalidIcsSubscriptionUrlError() from exc
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise IcsSubscriptionFetchError("The subscription host could not be resolved.") from exc
    resolved = {entry[4][0] for entry in addresses}
    if not resolved or any(not _is_public_address(address) for address in resolved):
        raise InvalidIcsSubscriptionUrlError(
            "Subscription URLs must resolve only to public network addresses."
        )
    return value


async def fetch_ics(url: str) -> bytes:
    safe_url = await validate_subscription_url(url)
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=FETCH_TIMEOUT_SECONDS,
            trust_env=False,
        ) as client:
            async with client.stream(
                "GET", safe_url, headers={"Accept": "text/calendar, text/plain;q=0.8"}
            ) as response:
                if response.is_redirect:
                    raise IcsSubscriptionFetchError(
                        "The subscription URL redirects; use its final HTTPS address instead."
                    )
                if response.status_code != 200:
                    raise IcsSubscriptionFetchError(
                        f"The subscription server returned HTTP {response.status_code}."
                    )
                length = response.headers.get("content-length")
                if length and length.isdigit() and int(length) > MAX_ICS_BYTES:
                    raise IcsFileTooLargeError()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_ICS_BYTES:
                        raise IcsFileTooLargeError()
                return bytes(content)
    except (IcsFileTooLargeError, IcsSubscriptionFetchError):
        raise
    except httpx.HTTPError as exc:
        raise IcsSubscriptionFetchError() from exc
