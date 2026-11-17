from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.auth.tokens import TokenIssuer, generate_refresh_token, hash_refresh_token

TEST_SECRET = "a" * 32


class FakeClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current


def test_token_issuer_creates_access_jwt_with_expected_claims() -> None:
    fixed_now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    clock = FakeClock(fixed_now)
    issuer = TokenIssuer(
        secret=TEST_SECRET,
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=30,
        clock=clock,
    )
    user_id = uuid4()

    token = issuer.issue_access_token(user_id)
    payload = jwt.decode(token, TEST_SECRET, algorithms=["HS256"], options={"verify_exp": False})

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert payload["iat"] == int(fixed_now.timestamp())
    assert payload["exp"] == int((fixed_now + timedelta(minutes=15)).timestamp())
    assert issuer.access_token_ttl_seconds == 900


def test_generate_and_hash_refresh_token() -> None:
    raw_one = generate_refresh_token()
    raw_two = generate_refresh_token()
    digest = hash_refresh_token(raw_one)

    assert raw_one != raw_two
    assert len(raw_one) >= 32
    assert len(digest) == 64
    assert digest == hash_refresh_token(raw_one)
    assert digest != raw_one


def test_decode_access_token_uses_injected_clock_for_expiration() -> None:
    past_now = datetime(2020, 1, 1, 12, 0, tzinfo=UTC)
    clock = FakeClock(past_now)
    issuer = TokenIssuer(
        secret=TEST_SECRET,
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=30,
        clock=clock,
    )
    user_id = uuid4()
    token = issuer.issue_access_token(user_id)

    assert issuer.decode_access_token(token) == user_id

    clock.current = past_now + timedelta(minutes=15)
    assert issuer.decode_access_token(token) is None


def test_decode_access_token_rejects_bad_signature_and_wrong_type() -> None:
    fixed_now = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
    issuer = TokenIssuer(
        secret=TEST_SECRET,
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=30,
        clock=FakeClock(fixed_now),
    )
    user_id = uuid4()
    wrong_sig = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": int(fixed_now.timestamp()),
            "exp": int((fixed_now + timedelta(minutes=15)).timestamp()),
        },
        "b" * 32,
        algorithm="HS256",
    )
    wrong_type = jwt.encode(
        {
            "sub": str(user_id),
            "type": "refresh",
            "iat": int(fixed_now.timestamp()),
            "exp": int((fixed_now + timedelta(minutes=15)).timestamp()),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    assert issuer.decode_access_token(wrong_sig) is None
    assert issuer.decode_access_token(wrong_type) is None
