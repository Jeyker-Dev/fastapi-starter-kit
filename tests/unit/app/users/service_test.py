from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.errors import BusinessRuleError
from app.users.domain import User
from app.users.errors import EmailAlreadyRegistered, PasswordTooShort
from app.users.service import UserService


class FakeClock:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def now(self) -> datetime:
        return self._current


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, User] = {}

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._by_id.values() if user.email == email), None)

    async def add(self, user: User) -> User:
        if await self.get_by_email(user.email) is not None:
            raise EmailAlreadyRegistered(user.email)
        self._by_id[user.id] = user
        return user


def _make_service(
    repo: FakeUserRepository | None = None,
    now: datetime | None = None,
) -> UserService:
    return UserService(
        users=repo or FakeUserRepository(),
        hasher=FakePasswordHasher(),
        clock=FakeClock(now or datetime(2026, 11, 16, 12, 0, tzinfo=UTC)),
    )


async def test_create_user_normalizes_email_and_uses_injected_clock() -> None:
    fixed_now = datetime(2026, 11, 16, 14, 30, tzinfo=UTC)
    repo = FakeUserRepository()
    service = _make_service(repo=repo, now=fixed_now)

    user = await service.create_user("  Alice@Example.COM  ", "correct-horse-12")

    assert user.email == "alice@example.com"
    assert user.password_hash == "hashed:correct-horse-12"
    assert user.is_active is True
    assert user.created_at == fixed_now
    assert user.updated_at == fixed_now
    assert await repo.get_by_id(user.id) == user


async def test_create_user_accepts_exactly_12_character_password() -> None:
    service = _make_service()

    user = await service.create_user("alice@example.com", "a" * 12)

    assert user.email == "alice@example.com"


async def test_create_user_rejects_password_shorter_than_12_chars() -> None:
    service = _make_service()

    with pytest.raises(PasswordTooShort) as exc_info:
        await service.create_user("alice@example.com", "a" * 11)

    assert isinstance(exc_info.value, BusinessRuleError)


async def test_create_user_rejects_duplicate_email_after_normalization() -> None:
    service = _make_service()
    await service.create_user("alice@example.com", "correct-horse-12")

    with pytest.raises(EmailAlreadyRegistered) as exc_info:
        await service.create_user("  ALICE@example.com ", "another-secret-12")

    assert isinstance(exc_info.value, BusinessRuleError)


async def test_get_by_id_and_get_by_email_normalize_lookup() -> None:
    service = _make_service()
    created = await service.create_user("alice@example.com", "correct-horse-12")

    assert await service.get_by_id(created.id) == created
    assert await service.get_by_id(uuid4()) is None
    assert await service.get_by_email("  ALICE@Example.COM ") == created
    assert await service.get_by_email("missing@example.com") is None
