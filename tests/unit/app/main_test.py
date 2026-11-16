from pathlib import Path

import pytest
from fastapi import FastAPI
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.config import Settings, get_settings
from app.main import app, create_app


def test_create_app_returns_fastapi_instance() -> None:
    created = create_app()

    assert isinstance(created, FastAPI)
    assert isinstance(app, FastAPI)


async def test_lifespan_initializes_engine_and_session_factory() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://app:app@localhost:5432/app",
        jwt_secret=SecretStr("a" * 32),
    )
    created = create_app(settings=settings)

    async with created.router.lifespan_context(created):
        assert created.state.settings is settings
        assert isinstance(created.state.engine, AsyncEngine)
        assert isinstance(created.state.session_factory, async_sessionmaker)


async def test_lifespan_fails_when_required_env_vars_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    get_settings.cache_clear()
    created = create_app()

    try:
        with pytest.raises(ValidationError):
            async with created.router.lifespan_context(created):
                pass
    finally:
        get_settings.cache_clear()
