import socket

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app

TEST_JWT_SECRET = SecretStr("test-secret-key-with-at-least-32-chars")


def _get_unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        address = sock.getsockname()
        return int(address[1])


@pytest.mark.usefixtures("ensure_test_database")
async def test_health_returns_ok_when_database_is_up(test_database_url: str) -> None:
    settings = Settings(
        _env_file=None,
        database_url=test_database_url,
        jwt_secret=TEST_JWT_SECRET,
    )
    application = create_app(settings=settings)

    async with (
        application.router.lifespan_context(application),
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://test",
        ) as client,
    ):
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_returns_unavailable_when_database_is_down() -> None:
    unused_port = _get_unused_port()
    settings = Settings(
        _env_file=None,
        database_url=f"postgresql+asyncpg://app:app@127.0.0.1:{unused_port}/app_test",
        jwt_secret=TEST_JWT_SECRET,
    )
    application = create_app(settings=settings)

    async with (
        application.router.lifespan_context(application),
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://test",
        ) as client,
    ):
        response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
