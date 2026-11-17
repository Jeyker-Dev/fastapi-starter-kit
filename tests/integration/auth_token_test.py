import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.passwords import PasswordHasher
from app.auth.tokens import hash_refresh_token
from app.config import Settings
from app.main import create_app

TEST_JWT_SECRET = "test-secret-key-with-at-least-32-chars"


class FakeClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current


@pytest.fixture
async def migrated_db_url(test_database_url: str, ensure_test_database: None) -> AsyncIterator[str]:
    _ = ensure_test_database
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", test_database_url)
    await asyncio.to_thread(command.upgrade, cfg, "head")

    engine = create_async_engine(test_database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE refresh_tokens, users CASCADE"))
        yield test_database_url
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE refresh_tokens, users CASCADE"))
        await engine.dispose()


async def _insert_user(
    database_url: str,
    *,
    email: str,
    password: str,
    is_active: bool,
    now: datetime,
) -> str:
    user_id = str(uuid4())
    password_hash = PasswordHasher().hash(password)
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO users "
                    "(id, email, password_hash, is_active, created_at, updated_at) "
                    "VALUES (:id, :email, :password_hash, :is_active, :created_at, :updated_at)"
                ),
                {
                    "id": user_id,
                    "email": email,
                    "password_hash": password_hash,
                    "is_active": is_active,
                    "created_at": now,
                    "updated_at": now,
                },
            )
    finally:
        await engine.dispose()
    return user_id


async def test_login_returns_tokens_and_persists_refresh_hash(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    user_id = await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=True,
        now=fixed_now,
    )
    settings = Settings(
        _env_file=None,
        database_url=migrated_db_url,
        jwt_secret=SecretStr(TEST_JWT_SECRET),
    )
    application = create_app(settings=settings, clock=FakeClock(fixed_now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        response = await client.post(
            "/auth/token",
            data={"username": "  ALICE@Example.com ", "password": "correct-horse-12"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900

    payload = jwt.decode(
        body["access_token"],
        TEST_JWT_SECRET,
        algorithms=["HS256"],
        options={"verify_exp": False},
    )
    assert payload["sub"] == user_id
    assert payload["type"] == "access"
    assert payload["iat"] == int(fixed_now.timestamp())
    assert payload["exp"] == int((fixed_now + timedelta(minutes=15)).timestamp())

    engine = create_async_engine(migrated_db_url)
    try:
        async with engine.connect() as conn:
            stored_hash = (
                await conn.execute(text("SELECT token_hash FROM refresh_tokens"))
            ).scalar_one()
            assert stored_hash == hash_refresh_token(body["refresh_token"])
            assert stored_hash != body["refresh_token"]
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    ("email", "password", "is_active"),
    [
        ("missing@example.com", "correct-horse-12", True),
        ("alice@example.com", "wrong-password-12", True),
        ("alice@example.com", "correct-horse-12", False),
    ],
)
async def test_login_rejects_invalid_or_inactive_credentials_with_same_401(
    migrated_db_url: str,
    email: str,
    password: str,
    is_active: bool,
) -> None:
    fixed_now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=is_active,
        now=fixed_now,
    )
    settings = Settings(
        _env_file=None,
        database_url=migrated_db_url,
        jwt_secret=SecretStr(TEST_JWT_SECRET),
    )
    application = create_app(settings=settings, clock=FakeClock(fixed_now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        response = await client.post(
            "/auth/token",
            data={"username": email, "password": password},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}
    assert response.headers.get("WWW-Authenticate") == "Bearer"
