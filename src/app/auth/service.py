from uuid import uuid4

from app.auth.domain import (
    PasswordVerifier,
    RefreshTokenRepository,
    TokenIssuerPort,
    TokenPair,
)
from app.auth.errors import InvalidCredentials
from app.users.service import UserService


class AuthService:
    """Application service handling authentication workflows."""

    def __init__(
        self,
        users: UserService,
        refresh_tokens: RefreshTokenRepository,
        passwords: PasswordVerifier,
        tokens: TokenIssuerPort,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._passwords = passwords
        self._tokens = tokens

    async def login(self, email: str, password: str) -> TokenPair:
        """Authenticate a user by email and password and issue a token pair."""
        user = await self._users.get_by_email(email)
        if user is None:
            self._passwords.verify_dummy(password)
            raise InvalidCredentials("Incorrect email or password")

        password_matches = self._passwords.verify(password, user.password_hash)
        if not password_matches or not user.is_active:
            raise InvalidCredentials("Incorrect email or password")

        family_id = uuid4()
        raw_refresh, refresh_record = self._tokens.new_refresh_token(
            user_id=user.id,
            family_id=family_id,
        )
        await self._refresh_tokens.add(refresh_record)

        access_token = self._tokens.issue_access_token(user_id=user.id)
        return TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=self._tokens.access_token_ttl_seconds,
        )
