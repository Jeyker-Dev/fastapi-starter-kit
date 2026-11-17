import argparse
import asyncio
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.auth.passwords import PasswordHasher
from app.clock import SystemClock
from app.config import get_settings
from app.db import create_engine, create_session_factory
from app.errors import BusinessRuleError
from app.users.domain import User
from app.users.repository import SqlAlchemyUserRepository
from app.users.service import UserService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an active user.")
    parser.add_argument("--email", required=True, help="User email address.")
    return parser.parse_args()


def _prompt_password() -> str:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    return password


async def _create_user(email: str, password: str) -> User:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        session_factory = create_session_factory(engine)
        async with session_factory() as session:
            service = UserService(
                users=SqlAlchemyUserRepository(session),
                hasher=PasswordHasher(),
                clock=SystemClock(),
            )
            return await service.create_user(email=email, password=password)
    finally:
        await engine.dispose()


def main() -> int:
    args = _parse_args()
    try:
        password = _prompt_password()
        user = asyncio.run(_create_user(email=args.email, password=password))
    except (BusinessRuleError, ValueError, ValidationError, SQLAlchemyError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("Aborted.", file=sys.stderr)
        return 1

    print(f"User created: {user.email} ({user.id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
