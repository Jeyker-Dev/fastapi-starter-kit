from app.errors import BusinessRuleError


class InvalidCredentials(BusinessRuleError):  # noqa: N818
    """Raised when login credentials are invalid or the user is inactive."""
