from uuid import UUID

from app.errors import BusinessRuleError


class InvalidCredentials(BusinessRuleError):  # noqa: N818
    """Raised when login credentials are invalid or the user is inactive."""


class InvalidRefreshToken(BusinessRuleError):  # noqa: N818
    """Raised when a refresh token is missing, expired, or belongs to an inactive user."""


class RefreshTokenReused(BusinessRuleError):  # noqa: N818
    """Raised when an already-revoked refresh token is presented again."""

    def __init__(self, family_id: UUID) -> None:
        self.family_id = family_id
        super().__init__("Invalid refresh token")
