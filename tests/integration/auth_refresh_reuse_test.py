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


async def test_reusing_rotated_token_returns_401(migrated_db_url: str) -> None:
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
        assert refresh_resp.status_code == 200

        clock.current = now + timedelta(minutes=2)
        reuse_resp = await client.post("/auth/refresh", json={"refresh_token": token_a})

    assert reuse_resp.status_code == 401
    assert reuse_resp.json() == {"detail": "Invalid refresh token"}


async def test_newest_token_in_reused_family_is_also_revoked(migrated_db_url: str) -> None:
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
        reuse_resp = await client.post("/auth/refresh", json={"refresh_token": token_a})
        assert reuse_resp.status_code == 401

        clock.current = now + timedelta(minutes=3)
        victim_resp = await client.post("/auth/refresh", json={"refresh_token": token_b})

    assert victim_resp.status_code == 401
    assert victim_resp.json() == {"detail": "Invalid refresh token"}


async def test_other_family_for_same_user_continues_working_after_reuse(
    migrated_db_url: str,
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
        login_1 = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        token_a = login_1.json()["refresh_token"]

        login_2 = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        token_c = login_2.json()["refresh_token"]

        clock.current = now + timedelta(minutes=1)
        await client.post("/auth/refresh", json={"refresh_token": token_a})

        clock.current = now + timedelta(minutes=2)
        reuse_resp = await client.post("/auth/refresh", json={"refresh_token": token_a})
        assert reuse_resp.status_code == 401

        clock.current = now + timedelta(minutes=3)
        other_family_resp = await client.post("/auth/refresh", json={"refresh_token": token_c})

    assert other_family_resp.status_code == 200
    assert other_family_resp.json()["refresh_token"] != token_c


async def test_reuse_revokes_only_affected_family_rows_in_database(
    migrated_db_url: str,
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

    rotate_time = now + timedelta(minutes=1)
    reuse_time = now + timedelta(minutes=2)

    async with (
        application.router.lifespan_context(application),
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client,
    ):
        login_1 = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        token_a = login_1.json()["refresh_token"]

        login_2 = await client.post(
            "/auth/token",
            data={"username": "alice@example.com", "password": "correct-horse-12"},
        )
        token_c = login_2.json()["refresh_token"]

        clock.current = rotate_time
        refresh_resp = await client.post("/auth/refresh", json={"refresh_token": token_a})
        token_b = refresh_resp.json()["refresh_token"]

        clock.current = reuse_time
        reuse_resp = await client.post("/auth/refresh", json={"refresh_token": token_a})
        assert reuse_resp.status_code == 401

    engine = create_async_engine(migrated_db_url)
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text("SELECT token_hash, family_id, revoked_at FROM refresh_tokens")
                )
            ).all()
    finally:
        await engine.dispose()

    by_hash = {row.token_hash: row for row in rows}
    row_a = by_hash[hash_refresh_token(token_a)]
    row_b = by_hash[hash_refresh_token(token_b)]
    row_c = by_hash[hash_refresh_token(token_c)]

    assert row_a.family_id == row_b.family_id
    assert row_c.family_id != row_a.family_id
    assert row_a.revoked_at == rotate_time
    assert row_b.revoked_at == reuse_time
    assert row_c.revoked_at is None
