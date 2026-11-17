import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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


def _make_settings(database_url: str) -> Settings:
    return Settings(
        _env_file=None,
        database_url=database_url,
        jwt_secret=SecretStr(TEST_JWT_SECRET),
    )


async def test_refresh_returns_distinct_token_pair_and_updates_expiration(
    migrated_db_url: str,
) -> None:
    login_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    clock = FakeClock(login_now)
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=True,
        now=login_now,
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=clock)

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        login_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        login_body = login_resp.json()

        refresh_now = login_now + timedelta(minutes=5)
        clock.current = refresh_now
        refresh_resp = await client.post(
            "/auth/refresh",
            json={"refresh_token": login_body["refresh_token"]},
        )

    assert refresh_resp.status_code == 200
    refresh_body = refresh_resp.json()
    assert refresh_body["token_type"] == "bearer"
    assert refresh_body["expires_in"] == 900
    assert refresh_body["access_token"] != login_body["access_token"]
    assert refresh_body["refresh_token"] != login_body["refresh_token"]

    engine = create_async_engine(migrated_db_url)
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT expires_at, revoked_at FROM refresh_tokens WHERE token_hash = :h"),
                    {"h": hash_refresh_token(refresh_body["refresh_token"])},
                )
            ).one()
            assert row.revoked_at is None
            assert row.expires_at == refresh_now + timedelta(days=30)
    finally:
        await engine.dispose()


async def test_used_refresh_token_cannot_be_used_again(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    await _insert_user(
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
        login_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        first_refresh = login_resp.json()["refresh_token"]

        first = await client.post("/auth/refresh", json={"refresh_token": first_refresh})
        assert first.status_code == 200

        second = await client.post("/auth/refresh", json={"refresh_token": first_refresh})

    assert second.status_code == 401
    assert second.json() == {"detail": "Invalid refresh token"}


async def test_new_refresh_token_can_be_used_for_next_refresh(migrated_db_url: str) -> None:
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    clock = FakeClock(now)
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=True,
        now=now,
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=clock)

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        login_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        token_1 = login_resp.json()["refresh_token"]

        clock.current = now + timedelta(minutes=1)
        resp_1 = await client.post("/auth/refresh", json={"refresh_token": token_1})
        assert resp_1.status_code == 200
        token_2 = resp_1.json()["refresh_token"]

        clock.current = now + timedelta(minutes=2)
        resp_2 = await client.post("/auth/refresh", json={"refresh_token": token_2})

    assert resp_2.status_code == 200
    assert resp_2.json()["refresh_token"] != token_2


async def test_refresh_returns_401_for_nonexistent_token(migrated_db_url: str) -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(fixed_now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": "nonexistent-opaque-token"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid refresh token"}


async def test_refresh_returns_401_for_expired_token(migrated_db_url: str) -> None:
    login_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    clock = FakeClock(login_now)
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        is_active=True,
        now=login_now,
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=clock)

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        login_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        clock.current = login_now + timedelta(days=30)
        response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid refresh token"}


async def test_refresh_returns_401_for_inactive_user(migrated_db_url: str) -> None:
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
        login_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        engine = create_async_engine(migrated_db_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("UPDATE users SET is_active = false WHERE id = :id"),
                    {"id": user_id},
                )
        finally:
            await engine.dispose()

        response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid refresh token"}
