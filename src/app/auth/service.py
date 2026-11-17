from uuid import uuid4

from app.auth.domain import (
    PasswordVerifier,
    RefreshTokenRepository,
    TokenIssuerPort,
    TokenPair,
)
from app.auth.errors import InvalidCredentials, InvalidRefreshToken
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

    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        """Validate and atomically rotate a refresh token, issuing a new pair."""
        token_hash = self._tokens.hash_refresh_token(raw_refresh_token)
        record = await self._refresh_tokens.get_by_hash(token_hash)
        now = self._tokens.now()
        if record is None or record.revoked_at is not None or record.expires_at <= now:
            raise InvalidRefreshToken("Invalid refresh token")

        user = await self._users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshToken("Invalid refresh token")

        new_raw, replacement = self._tokens.new_refresh_token(
            user_id=user.id,
            family_id=record.family_id,
        )
        rotated = await self._refresh_tokens.rotate(
            token_id=record.id,
            revoked_at=now,
            replacement=replacement,
        )
        if not rotated:
            raise InvalidRefreshToken("Invalid refresh token")

        access_token = self._tokens.issue_access_token(user_id=user.id)
        return TokenPair(
            access_token=access_token,
            refresh_token=new_raw,
            expires_in=self._tokens.access_token_ttl_seconds,
        )
