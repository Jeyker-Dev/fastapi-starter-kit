from app.auth.passwords import PasswordHasher


def test_password_hasher_hashes_with_argon2_and_verifies() -> None:
    hasher = PasswordHasher()

    hashed = hasher.hash("correct-horse-12")

    assert hashed != "correct-horse-12"
    assert hashed.startswith("$argon2")
    assert hasher.verify("correct-horse-12", hashed) is True
    assert hasher.verify("wrong-password-12", hashed) is False
