import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.passwords import PasswordHasher

SCRIPT_PATH = Path("scripts/create_user.py")
TEST_JWT_SECRET = "test-secret-key-with-at-least-32-chars"


@pytest.fixture
async def migrated_test_db(
    test_database_url: str, ensure_test_database: None
) -> AsyncIterator[str]:
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


def _run_create_user(
    database_url: str,
    email: str,
    stdin_text: str,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["JWT_SECRET"] = TEST_JWT_SECRET
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--email", email],
        input=stdin_text,
        text=True,
        capture_output=True,
        start_new_session=True,
        env=env,
        check=False,
    )


async def test_create_user_script_creates_active_user_with_normalized_email(
    migrated_test_db: str,
) -> None:
    result = await asyncio.to_thread(
        _run_create_user,
        migrated_test_db,
        "  Alice@Example.COM ",
        "correct-horse-12\ncorrect-horse-12\n",
    )

    assert result.returncode == 0
    assert "alice@example.com" in result.stdout

    engine = create_async_engine(migrated_test_db)
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT email, password_hash, is_active FROM users WHERE email = :email"),
                    {"email": "alice@example.com"},
                )
            ).one()
            assert row.email == "alice@example.com"
            assert row.is_active is True
            assert PasswordHasher().verify("correct-horse-12", row.password_hash) is True
    finally:
        await engine.dispose()


async def test_create_user_script_fails_without_traceback_on_duplicate_email(
    migrated_test_db: str,
) -> None:
    first = await asyncio.to_thread(
        _run_create_user,
        migrated_test_db,
        "alice@example.com",
        "correct-horse-12\ncorrect-horse-12\n",
    )
    assert first.returncode == 0

    duplicate = await asyncio.to_thread(
        _run_create_user,
        migrated_test_db,
        "ALICE@example.com",
        "another-secret-12\nanother-secret-12\n",
    )

    assert duplicate.returncode != 0
    assert "Traceback" not in duplicate.stderr
    assert "Traceback" not in duplicate.stdout
    assert duplicate.stderr.strip() != ""


async def test_create_user_script_fails_without_traceback_on_short_password(
    migrated_test_db: str,
) -> None:
    result = await asyncio.to_thread(
        _run_create_user,
        migrated_test_db,
        "bob@example.com",
        "short-pass\nshort-pass\n",
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert result.stderr.strip() != ""


async def test_create_user_script_fails_when_passwords_do_not_match(
    migrated_test_db: str,
) -> None:
    result = await asyncio.to_thread(
        _run_create_user,
        migrated_test_db,
        "carol@example.com",
        "correct-horse-12\ndifferent-pass-12\n",
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert result.stderr.strip() != ""
