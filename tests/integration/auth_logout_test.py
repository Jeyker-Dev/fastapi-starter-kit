import asyncio
import logging
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
                    "VALUES (:id, :email, :password_hash, true, :created_at, :updated_at)"
                ),
                {
                    "id": user_id,
                    "email": email,
                    "password_hash": password_hash,
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


async def test_logout_returns_204_and_invalidates_refresh_token(migrated_db_url: str) -> None:
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(now))
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        now=now,
    )

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        login_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        logout_resp = await client.post("/auth/logout", json={"refresh_token": refresh_token})
        assert logout_resp.status_code == 204
        assert logout_resp.content == b""

        refresh_resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert refresh_resp.status_code == 401
    assert refresh_resp.json() == {"detail": "Invalid refresh token"}


async def test_logout_after_refresh_revokes_entire_family(migrated_db_url: str) -> None:
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    clock = FakeClock(now)
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
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
        token_a = login_resp.json()["refresh_token"]

        clock.current = now + timedelta(minutes=1)
        refresh_resp = await client.post("/auth/refresh", json={"refresh_token": token_a})
        token_b = refresh_resp.json()["refresh_token"]

        clock.current = now + timedelta(minutes=2)
        logout_resp = await client.post("/auth/logout", json={"refresh_token": token_b})
        assert logout_resp.status_code == 204
        assert logout_resp.content == b""

        resp_a = await client.post("/auth/refresh", json={"refresh_token": token_a})
        resp_b = await client.post("/auth/refresh", json={"refresh_token": token_b})

    assert resp_a.status_code == 401
    assert resp_b.status_code == 401


async def test_logout_with_nonexistent_token_returns_204(migrated_db_url: str) -> None:
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        response = await client.post(
            "/auth/logout",
            json={"refresh_token": "nonexistent-opaque-token"},
        )

    assert response.status_code == 204
    assert response.content == b""


async def test_logout_twice_with_same_token_returns_204_both_times(
    migrated_db_url: str,
) -> None:
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        now=now,
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=FakeClock(now))

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        login_resp = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        first = await client.post("/auth/logout", json={"refresh_token": refresh_token})
        second = await client.post("/auth/logout", json={"refresh_token": refresh_token})

    assert first.status_code == 204
    assert first.content == b""
    assert second.status_code == 204
    assert second.content == b""


async def test_logout_does_not_affect_other_session_family(migrated_db_url: str) -> None:
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    clock = FakeClock(now)
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
        now=now,
    )
    application = create_app(settings=_make_settings(migrated_db_url), clock=clock)

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        login_1 = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        token_1 = login_1.json()["refresh_token"]

        login_2 = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        token_2 = login_2.json()["refresh_token"]

        logout_resp = await client.post("/auth/logout", json={"refresh_token": token_1})
        assert logout_resp.status_code == 204

        clock.current = now + timedelta(minutes=1)
        other_refresh = await client.post("/auth/refresh", json={"refresh_token": token_2})

    assert other_refresh.status_code == 200
    assert other_refresh.json()["refresh_token"] != token_2


async def test_logout_with_already_revoked_token_logs_no_warning(
    migrated_db_url: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    clock = FakeClock(now)
    await _insert_user(
        migrated_db_url,
        email="alice@example.com",
        password="correct-horse-12",
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
        token_a = login_resp.json()["refresh_token"]

        clock.current = now + timedelta(minutes=1)
        await client.post("/auth/refresh", json={"refresh_token": token_a})

        clock.current = now + timedelta(minutes=2)
        with caplog.at_level(logging.WARNING, logger="app"):
            logout_resp = await client.post("/auth/logout", json={"refresh_token": token_a})

    assert logout_resp.status_code == 204
    assert logout_resp.content == b""
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
