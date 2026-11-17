from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

_DEFAULT_PASSWORD_HASH = PasswordHash.recommended()
_DUMMY_HASH = _DEFAULT_PASSWORD_HASH.hash("dummy-password-for-timing-protection")


class PasswordHasher:
    """Argon2 password hasher backed by pwdlib."""

    def __init__(self) -> None:
        self._hasher = _DEFAULT_PASSWORD_HASH

    def hash(self, password: str) -> str:
        """Hash a plain-text password using Argon2."""
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """Verify a plain-text password against an Argon2 hash."""
        try:
            return self._hasher.verify(password, password_hash)
        except UnknownHashError:
            return False

    def verify_dummy(self, password: str) -> None:
        """Run Argon2 verification against a dummy hash for constant-time rejection."""
        self.verify(password, _DUMMY_HASH)
