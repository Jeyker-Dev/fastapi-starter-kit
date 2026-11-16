from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

MIN_PASSWORD_LENGTH = 12


def normalize_email(email: str) -> str:
    """Strip surrounding whitespace and lowercase the email address."""
    return email.strip().lower()


@dataclass(frozen=True, slots=True)
class User:
    """Domain entity representing an application user."""

    id: UUID
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PasswordHasher(Protocol):
    """Port for hashing plain-text passwords."""

    def hash(self, password: str) -> str: ...


class UserRepository(Protocol):
    """Persistence port for user entities."""

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def add(self, user: User) -> User: ...
