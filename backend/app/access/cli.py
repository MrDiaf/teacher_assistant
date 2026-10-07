"""Owner access commands, run on the host through `make password` and `make funnel-on`.

    python -m app.access.cli set-password   # prompt, store, clear cooldowns, sign out sessions
    python -m app.access.cli check          # exit 0 when a password is set, 1 otherwise
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from app.access.service import get_password_record, set_password, validate_new_password
from app.database.session import engine, session_factory


async def _set_password(password: str) -> None:
    try:
        async with session_factory() as session:
            await set_password(session, password)
    finally:
        await engine.dispose()


async def _password_is_set() -> bool:
    try:
        async with session_factory() as session:
            return await get_password_record(session) is not None
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.access.cli")
    parser.add_argument("command", choices=("set-password", "check"))
    command = parser.parse_args(argv).command

    if command == "check":
        if asyncio.run(_password_is_set()):
            print("An owner password is set.")
            return 0
        print("No owner password is set. Run `make password` first.", file=sys.stderr)
        return 1

    password = getpass.getpass("New Teacher Assistant password: ")
    try:
        validate_new_password(password)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if getpass.getpass("Repeat the password: ") != password:
        print("The passwords do not match. Nothing was changed.", file=sys.stderr)
        return 1
    asyncio.run(_set_password(password))
    print("Password saved. All sign-in cooldowns were cleared and every browser was signed out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
