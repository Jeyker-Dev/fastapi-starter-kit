from app.errors import BusinessRuleError


class InvalidCredentials(BusinessRuleError):  # noqa: N818
    """Raised when login credentials are invalid or the user is inactive."""


class InvalidRefreshToken(BusinessRuleError):  # noqa: N818
    """Raised when a refresh token is missing, expired, revoked, or belongs to an inactive user."""
