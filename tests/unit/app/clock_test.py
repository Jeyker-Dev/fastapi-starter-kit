from datetime import UTC, datetime

from app.clock import Clock, SystemClock


def test_system_clock_returns_utc_datetime() -> None:
    clock: Clock = SystemClock()

    now = clock.now()

    assert isinstance(now, datetime)
    assert now.tzinfo is UTC
