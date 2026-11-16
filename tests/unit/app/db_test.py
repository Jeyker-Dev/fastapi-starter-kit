from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from app.db import Base, create_engine, create_session_factory

TEST_DATABASE_URL = "postgresql+asyncpg://app:app@localhost:5432/app"


def test_base_inherits_from_async_attrs_and_declarative_base() -> None:
    assert issubclass(Base, AsyncAttrs)
    assert issubclass(Base, DeclarativeBase)


def test_create_engine_returns_async_engine_with_url() -> None:
    engine = create_engine(TEST_DATABASE_URL)

    assert isinstance(engine, AsyncEngine)
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.database == "app"


def test_create_session_factory_configures_async_session() -> None:
    engine = create_engine(TEST_DATABASE_URL)

    session_factory = create_session_factory(engine)

    assert isinstance(session_factory, async_sessionmaker)
    assert session_factory.kw.get("expire_on_commit") is False
    session = session_factory()
    assert isinstance(session, AsyncSession)
