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


def _make_settings(database_url: str) -> Settings:
    return Settings(
        _env_file=None,
        database_url=database_url,
        jwt_secret=SecretStr(TEST_JWT_SECRET),
    )


def _assert_unauthorized(
    response_status: int, response_json: object, auth_header: str | None
) -> None:
    assert response_status == 401
    assert response_json == {"detail": "Could not validate credentials"}
    assert auth_header == "Bearer"


async def test_me_returns_authenticated_user_without_password_hash(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    user_id = await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=True,
        now=fixed_now,
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(fixed_now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        token_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        access_token = token_resp.json()["access_token"]
        me_resp = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert me_resp.status_code == 200
    body = me_resp.json()
    assert set(body) == {"id", "email", "is_active", "created_at"}
    assert "password_hash" not in body
    assert body["id"] == user_id
    assert body["email"] == "alice@example.com"
    assert body["is_active"] is True
    assert datetime.fromisoformat(body["created_at"]) == fixed_now


async def test_me_returns_401_when_token_is_missing(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(fixed_now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        response = await client.get("/users/me")

    _assert_unauthorized(
        response.status_code,
        response.json(),
        response.headers.get("WWW-Authenticate"),
    )


async def test_me_returns_401_when_token_has_invalid_signature(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    user_id = await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=True,
        now=fixed_now,
    )
    bad_token = jwt.encode(
        {
            "sub": user_id,
            "type": "access",
            "iat": int(fixed_now.timestamp()),
            "exp": int((fixed_now + timedelta(minutes=15)).timestamp()),
        },
        "wrong-secret-key-with-at-least-32-chars",
        algorithm="HS256",
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(fixed_now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {bad_token}"},
        )

    _assert_unauthorized(
        response.status_code,
        response.json(),
        response.headers.get("WWW-Authenticate"),
    )


async def test_me_returns_401_when_token_is_expired(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=True,
        now=fixed_now,
    )
    clock = FakeClock(fixed_now)
    application = create_app(settings=_make_settings(migrated_db_url), clock=clock)

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        token_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        access_token = token_resp.json()["access_token"]

        clock.current = fixed_now + timedelta(minutes=15)
        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    _assert_unauthorized(
        response.status_code,
        response.json(),
        response.headers.get("WWW-Authenticate"),
    )


async def test_me_returns_401_when_token_type_is_not_access(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    user_id = await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=True,
        now=fixed_now,
    )
    wrong_type_token = jwt.encode(
        {
            "sub": user_id,
            "type": "refresh",
            "iat": int(fixed_now.timestamp()),
            "exp": int((fixed_now + timedelta(minutes=15)).timestamp()),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(fixed_now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {wrong_type_token}"},
        )

    _assert_unauthorized(
        response.status_code,
        response.json(),
        response.headers.get("WWW-Authenticate"),
    )


async def test_me_returns_401_when_user_does_not_exist(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    orphan_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "type": "access",
            "iat": int(fixed_now.timestamp()),
            "exp": int((fixed_now + timedelta(minutes=15)).timestamp()),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(fixed_now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {orphan_token}"},
        )

    _assert_unauthorized(
        response.status_code,
        response.json(),
        response.headers.get("WWW-Authenticate"),
    )


async def test_me_returns_401_when_user_is_inactive(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    user_id = await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=True,
        now=fixed_now,
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(fixed_now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        token_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        access_token = token_resp.json()["access_token"]

        engine = create_async_engine(migrated_db_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("UPDATE users SET is_active = false WHERE id = :id"),
                    {"id": user_id},
                )
        finally:
            await engine.dispose()

        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    _assert_unauthorized(
        response.status_code,
        response.json(),
        response.headers.get("WWW-Authenticate"),
    )
