from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

import app.users.domain as domain_module
from app.users.domain import User, normalize_email


def test_normalize_email_strips_whitespace_and_lowercases() -> None:
    assert normalize_email("  Alice.Example@Domain.COM \n") == "alice.example@domain.com"


def test_user_dataclass_is_frozen() -> None:
    now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    user = User(
        id=uuid4(),
        email="alice@example.com",
        password_hash="hashed",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(FrozenInstanceError):
        user.email = "other@example.com"  # type: ignore[misc]


def test_users_domain_does_not_import_framework_libraries() -> None:
    assert domain_module.__file__ is not None
    source_text = Path(domain_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("fastapi", "pydantic", "sqlalchemy"):
        assert forbidden not in source_text
