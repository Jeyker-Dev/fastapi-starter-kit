from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Port for obtaining the current UTC timestamp."""

    def now(self) -> datetime: ...


class SystemClock:
    """Production clock returning the current UTC datetime."""

    def now(self) -> datetime:
        return datetime.now(UTC)
