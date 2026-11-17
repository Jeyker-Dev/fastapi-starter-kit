from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Pair of issued access and refresh tokens."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


@dataclass(frozen=True, slots=True)
class RefreshToken:
    """Domain entity representing a stored refresh token."""

    id: UUID
    user_id: UUID
    family_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime


class RefreshTokenRepository(Protocol):
    """Persistence port for refresh tokens."""

    async def add(self, token: RefreshToken) -> RefreshToken: ...


class PasswordVerifier(Protocol):
    """Port for verifying passwords against stored hashes."""

    def verify(self, password: str, password_hash: str) -> bool: ...

    def verify_dummy(self, password: str) -> None: ...


class TokenIssuerPort(Protocol):
    """Port for issuing access JWTs and refresh tokens."""

    @property
    def access_token_ttl_seconds(self) -> int: ...

    def issue_access_token(self, user_id: UUID) -> str: ...

    def new_refresh_token(self, user_id: UUID, family_id: UUID) -> tuple[str, RefreshToken]: ...
