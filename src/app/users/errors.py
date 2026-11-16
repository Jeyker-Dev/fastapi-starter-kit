from app.errors import BusinessRuleError


class EmailAlreadyRegistered(BusinessRuleError):  # noqa: N818
    """Raised when attempting to register a user with an existing email."""


class PasswordTooShort(BusinessRuleError):  # noqa: N818
    """Raised when a user password is shorter than the required minimum length."""
