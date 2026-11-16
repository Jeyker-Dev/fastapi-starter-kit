from uuid import UUID, uuid4

from app.clock import Clock
from app.users.domain import (
    MIN_PASSWORD_LENGTH,
    PasswordHasher,
    User,
    UserRepository,
    normalize_email,
)
from app.users.errors import EmailAlreadyRegistered, PasswordTooShort


class UserService:
    """Application service for user management use cases."""

    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._clock = clock

    async def create_user(self, email: str, password: str) -> User:
        """Validate, normalize, hash password, and persist a new active user."""
        normalized_email = normalize_email(email)
        if len(password) < MIN_PASSWORD_LENGTH:
            raise PasswordTooShort(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
            )

        existing = await self._users.get_by_email(normalized_email)
        if existing is not None:
            raise EmailAlreadyRegistered(f"Email {normalized_email!r} is already registered.")

        now = self._clock.now()
        user = User(
            id=uuid4(),
            email=normalized_email,
            password_hash=self._hasher.hash(password),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        return await self._users.add(user)

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a user by primary identifier."""
        return await self._users.get_by_id(user_id)

    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a user by normalized email address."""
        return await self._users.get_by_email(normalize_email(email))
