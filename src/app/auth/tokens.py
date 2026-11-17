import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import jwt

from app.auth.domain import RefreshToken
from app.clock import Clock

JWT_ALGORITHM = "HS256"
SECONDS_PER_MINUTE = 60


def generate_refresh_token() -> str:
    """Generate a cryptographically random opaque refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Compute the SHA-256 hex digest of an opaque refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TokenIssuer:
    """Issues signed HS256 access JWTs and opaque refresh tokens."""

    def __init__(
        self,
        secret: str,
        access_token_ttl_minutes: int,
        refresh_token_ttl_days: int,
        clock: Clock,
    ) -> None:
        self._secret = secret
        self._access_token_ttl_minutes = access_token_ttl_minutes
        self._refresh_token_ttl_days = refresh_token_ttl_days
        self._clock = clock

    @property
    def access_token_ttl_seconds(self) -> int:
        """Return access token lifetime in seconds."""
        return self._access_token_ttl_minutes * SECONDS_PER_MINUTE

    def now(self) -> datetime:
        """Return the current UTC timestamp from the injected Clock."""
        return self._clock.now()

    def hash_refresh_token(self, raw_token: str) -> str:
        """Hash an opaque refresh token using SHA-256."""
        return hash_refresh_token(raw_token)

    def issue_access_token(self, user_id: UUID) -> str:
        """Sign an HS256 JWT access token for the given user ID."""
        now = self._clock.now()
        expires_at = now + timedelta(minutes=self._access_token_ttl_minutes)
        payload: dict[str, str | int] = {
            "sub": str(user_id),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm=JWT_ALGORITHM)

    def new_refresh_token(self, user_id: UUID, family_id: UUID) -> tuple[str, RefreshToken]:
        """Create a raw opaque refresh token and its hashed domain record."""
        now = self._clock.now()
        raw_token = generate_refresh_token()
        token = RefreshToken(
            id=uuid4(),
            user_id=user_id,
            family_id=family_id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=now + timedelta(days=self._refresh_token_ttl_days),
            revoked_at=None,
            created_at=now,
        )
        return raw_token, token

    def decode_access_token(self, token: str) -> UUID | None:
        """Verify an access JWT using the injected Clock and return its user ID."""
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False, "require": ["exp", "sub", "type"]},
            )
        except jwt.InvalidTokenError:
            return None

        if payload.get("type") != "access":
            return None

        exp = payload.get("exp")
        if isinstance(exp, bool) or not isinstance(exp, int):
            return None
        if exp <= int(self._clock.now().timestamp()):
            return None

        sub = payload.get("sub")
        if not isinstance(sub, str):
            return None
        try:
            return UUID(sub)
        except ValueError:
            return None
