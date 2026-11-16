from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings

VALID_JWT_SECRET = "a" * 32
VALID_DATABASE_URL = "postgresql+asyncpg://app:app@db:5432/app"


def _clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "DATABASE_URL",
        "JWT_SECRET",
        "ACCESS_TOKEN_TTL_MINUTES",
        "REFRESH_TOKEN_TTL_DAYS",
    ):
        monkeypatch.delenv(var, raising=False)


def test_settings_loads_with_required_env_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)

    settings = Settings(_env_file=None)

    assert settings.database_url == VALID_DATABASE_URL
    assert settings.jwt_secret.get_secret_value() == VALID_JWT_SECRET
    assert settings.access_token_ttl_minutes == 15
    assert settings.refresh_token_ttl_days == 30


def test_settings_overrides_optional_ttls(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("ACCESS_TOKEN_TTL_MINUTES", "10")
    monkeypatch.setenv("REFRESH_TOKEN_TTL_DAYS", "7")

    settings = Settings(_env_file=None)

    assert settings.access_token_ttl_minutes == 10
    assert settings.refresh_token_ttl_days == 7


def test_settings_fails_when_database_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "database_url" in str(exc_info.value)


def test_settings_fails_when_database_url_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "database_url" in str(exc_info.value)


def test_settings_fails_when_jwt_secret_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "jwt_secret" in str(exc_info.value)


def test_settings_fails_when_jwt_secret_is_shorter_than_32_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", "a" * 31)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "jwt_secret" in str(exc_info.value)


def test_settings_ignores_compose_database_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("POSTGRES_USER", "app")
    monkeypatch.setenv("POSTGRES_PASSWORD", "app")
    monkeypatch.setenv("POSTGRES_DB", "app")

    settings = Settings(_env_file=None)

    assert settings.database_url == VALID_DATABASE_URL


def test_get_settings_caches_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    get_settings.cache_clear()

    first = get_settings()
    second = get_settings()

    assert first is second
    get_settings.cache_clear()


def test_env_example_lists_all_documented_variables() -> None:
    env_example = Path(".env.example")
    assert env_example.exists()

    keys = {
        line.split("=", 1)[0].strip()
        for line in env_example.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "=" in line
    }
    expected_keys = {
        "DATABASE_URL",
        "JWT_SECRET",
        "ACCESS_TOKEN_TTL_MINUTES",
        "REFRESH_TOKEN_TTL_DAYS",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    }
    assert expected_keys.issubset(keys)
