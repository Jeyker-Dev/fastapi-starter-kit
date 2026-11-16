import asyncio

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import Base


def _alembic_config(database_url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _get_table_names(conn: Connection) -> set[str]:
    return set(inspect(conn).get_table_names())


def _get_columns(conn: Connection, table: str) -> dict[str, dict[str, object]]:
    return {col["name"]: dict(col) for col in inspect(conn).get_columns(table)}


def _has_unique_column(conn: Connection, table: str, column: str) -> bool:
    inspector = inspect(conn)
    uniques = inspector.get_unique_constraints(table)
    indexes = inspector.get_indexes(table)
    return any(uc["column_names"] == [column] for uc in uniques) or any(
        idx.get("unique") and idx["column_names"] == [column] for idx in indexes
    )


def _has_index_on(conn: Connection, table: str, column: str) -> bool:
    indexes = inspect(conn).get_indexes(table)
    return any(idx["column_names"] == [column] for idx in indexes)


@pytest.mark.usefixtures("ensure_test_database")
async def test_initial_migration_creates_and_drops_auth_tables(
    test_database_url: str,
) -> None:
    cfg = _alembic_config(test_database_url)
    await asyncio.to_thread(command.downgrade, cfg, "base")
    await asyncio.to_thread(command.upgrade, cfg, "head")

    engine = create_async_engine(test_database_url)
    try:
        async with engine.connect() as conn:
            tables = await conn.run_sync(_get_table_names)
            assert {"users", "refresh_tokens"}.issubset(tables)

            users_cols = await conn.run_sync(_get_columns, "users")
            assert set(users_cols) == {
                "id",
                "email",
                "password_hash",
                "is_active",
                "created_at",
                "updated_at",
            }
            assert users_cols["is_active"]["nullable"] is False
            assert await conn.run_sync(_has_unique_column, "users", "email")

            rt_cols = await conn.run_sync(_get_columns, "refresh_tokens")
            assert set(rt_cols) == {
                "id",
                "user_id",
                "family_id",
                "token_hash",
                "expires_at",
                "revoked_at",
                "created_at",
            }
            assert rt_cols["revoked_at"]["nullable"] is True
            assert await conn.run_sync(_has_unique_column, "refresh_tokens", "token_hash")
            assert await conn.run_sync(_has_index_on, "refresh_tokens", "user_id")
            assert await conn.run_sync(_has_index_on, "refresh_tokens", "family_id")

            fks = await conn.run_sync(lambda c: inspect(c).get_foreign_keys("refresh_tokens"))
            assert len(fks) == 1
            assert fks[0]["referred_table"] == "users"
            assert fks[0]["referred_columns"] == ["id"]
            assert fks[0]["constrained_columns"] == ["user_id"]
            assert fks[0]["options"].get("ondelete") == "CASCADE"

        await asyncio.to_thread(command.downgrade, cfg, "base")

        async with engine.connect() as conn:
            tables_after = await conn.run_sync(_get_table_names)
            assert "users" not in tables_after
            assert "refresh_tokens" not in tables_after
    finally:
        await engine.dispose()
        assert Base.metadata is not None
