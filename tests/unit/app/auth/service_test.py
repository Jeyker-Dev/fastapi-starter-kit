from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.auth.domain import RefreshToken
from app.auth.errors import InvalidCredentials, InvalidRefreshToken
from app.auth.service import AuthService
from app.auth.tokens import TokenIssuer, hash_refresh_token
from app.errors import BusinessRuleError
from app.users.domain import User
from app.users.service import UserService

TEST_SECRET = "a" * 32


class FakeClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current


class FakePasswordHasher:
    def __init__(self) -> None:
        self.dummy_checks = 0

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"

    def verify_dummy(self, password: str) -> None:
        _ = password
        self.dummy_checks += 1


class FakeUserRepository:
    def __init__(self) -> None:
        self.by_id: dict[UUID, User] = {}

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.by_id.values() if u.email == email), None)

    async def add(self, user: User) -> User:
        self.by_id[user.id] = user
        return user


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self.tokens: list[RefreshToken] = []

    async def add(self, token: RefreshToken) -> RefreshToken:
        self.tokens.append(token)
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self.tokens if t.token_hash == token_hash), None)

    async def rotate(
        self,
        token_id: UUID,
        revoked_at: datetime,
        replacement: RefreshToken,
    ) -> bool:
        for idx, token in enumerate(self.tokens):
            if token.id == token_id and token.revoked_at is None:
                self.tokens[idx] = replace(token, revoked_at=revoked_at)
                self.tokens.append(replacement)
                return True
        return False


def _make_auth_setup(
    *,
    now: datetime | None = None,
) -> tuple[
    AuthService, UserService, FakeUserRepository, FakeRefreshTokenRepository, FakePasswordHasher
]:
    clock = FakeClock(now or datetime(2026, 11, 16, 12, 0, tzinfo=UTC))
    hasher = FakePasswordHasher()
    user_repo = FakeUserRepository()
    token_repo = FakeRefreshTokenRepository()
    user_service = UserService(users=user_repo, hasher=hasher, clock=clock)
    token_issuer = TokenIssuer(
        secret=TEST_SECRET,
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=30,
        clock=clock,
    )
    auth_service = AuthService(
        users=user_service,
        refresh_tokens=token_repo,
        passwords=hasher,
        tokens=token_issuer,
    )
    return auth_service, user_service, user_repo, token_repo, hasher


async def test_login_succeeds_and_stores_hashed_refresh_token() -> None:
    now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    auth_service, user_service, _, token_repo, _ = _make_auth_setup(now=now)
    await user_service.create_user("alice@example.com", "correct-horse-12")

    pair = await auth_service.login("  ALICE@Example.COM ", "correct-horse-12")

    assert pair.token_type == "bearer"
    assert pair.expires_in == 900
    assert pair.access_token != ""
    assert pair.refresh_token != ""
    assert len(token_repo.tokens) == 1
    stored = token_repo.tokens[0]
    assert stored.token_hash == hash_refresh_token(pair.refresh_token)
    assert stored.token_hash != pair.refresh_token
    assert stored.created_at == now
    assert stored.expires_at == now + timedelta(days=30)
    assert stored.revoked_at is None


async def test_each_login_creates_distinct_family_id() -> None:
    auth_service, user_service, _, token_repo, _ = _make_auth_setup()
    await user_service.create_user("alice@example.com", "correct-horse-12")

    await auth_service.login("alice@example.com", "correct-horse-12")
    await auth_service.login("alice@example.com", "correct-horse-12")

    assert len(token_repo.tokens) == 2
    assert token_repo.tokens[0].family_id != token_repo.tokens[1].family_id


async def test_login_with_unknown_email_verifies_dummy_and_raises_invalid_credentials() -> None:
    auth_service, _, _, _, hasher = _make_auth_setup()

    with pytest.raises(InvalidCredentials) as exc_info:
        await auth_service.login("missing@example.com", "correct-horse-12")

    assert isinstance(exc_info.value, BusinessRuleError)
    assert hasher.dummy_checks == 1


async def test_login_with_wrong_password_raises_invalid_credentials() -> None:
    auth_service, user_service, _, _, _ = _make_auth_setup()
    await user_service.create_user("alice@example.com", "correct-horse-12")

    with pytest.raises(InvalidCredentials):
        await auth_service.login("alice@example.com", "wrong-password-12")


async def test_login_with_inactive_user_raises_invalid_credentials() -> None:
    auth_service, _, user_repo, _, _ = _make_auth_setup()
    now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    inactive = User(
        id=uuid4(),
        email="inactive@example.com",
        password_hash="hashed:correct-horse-12",
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    await user_repo.add(inactive)

    with pytest.raises(InvalidCredentials):
        await auth_service.login("inactive@example.com", "correct-horse-12")


async def test_refresh_rotates_token_preserving_family_and_extending_ttl() -> None:
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    clock = FakeClock(now)
    hasher = FakePasswordHasher()
    user_repo = FakeUserRepository()
    token_repo = FakeRefreshTokenRepository()
    user_service = UserService(users=user_repo, hasher=hasher, clock=clock)
    token_issuer = TokenIssuer(
        secret=TEST_SECRET,
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=30,
        clock=clock,
    )
    auth_service = AuthService(
        users=user_service,
        refresh_tokens=token_repo,
        passwords=hasher,
        tokens=token_issuer,
    )
    await user_service.create_user("alice@example.com", "correct-horse-12")
    initial = await auth_service.login("alice@example.com", "correct-horse-12")

    refresh_time = now + timedelta(days=5)
    clock.current = refresh_time
    rotated = await auth_service.refresh(initial.refresh_token)

    assert rotated.refresh_token != initial.refresh_token
    assert len(token_repo.tokens) == 2
    old_record, new_record = token_repo.tokens
    assert old_record.revoked_at == refresh_time
    assert new_record.family_id == old_record.family_id
    assert new_record.revoked_at is None
    assert new_record.expires_at == refresh_time + timedelta(days=30)


async def test_refresh_rejects_missing_expired_and_inactive_tokens() -> None:
    now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    clock = FakeClock(now)
    hasher = FakePasswordHasher()
    user_repo = FakeUserRepository()
    token_repo = FakeRefreshTokenRepository()
    user_service = UserService(users=user_repo, hasher=hasher, clock=clock)
    token_issuer = TokenIssuer(
        secret=TEST_SECRET,
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=30,
        clock=clock,
    )
    auth_service = AuthService(
        users=user_service,
        refresh_tokens=token_repo,
        passwords=hasher,
        tokens=token_issuer,
    )
    user = await user_service.create_user("alice@example.com", "correct-horse-12")
    pair = await auth_service.login("alice@example.com", "correct-horse-12")

    with pytest.raises(InvalidRefreshToken) as exc_info:
        await auth_service.refresh("does-not-exist")
    assert isinstance(exc_info.value, BusinessRuleError)

    clock.current = now + timedelta(days=30)
    with pytest.raises(InvalidRefreshToken):
        await auth_service.refresh(pair.refresh_token)

    clock.current = now + timedelta(minutes=1)
    user_repo.by_id[user.id] = replace(user, is_active=False)
    with pytest.raises(InvalidRefreshToken):
        await auth_service.refresh(pair.refresh_token)
