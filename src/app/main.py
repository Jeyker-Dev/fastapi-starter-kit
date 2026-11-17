from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.auth.api import router as auth_router
from app.auth.errors import InvalidCredentials, InvalidRefreshToken
from app.auth.passwords import PasswordHasher
from app.clock import Clock, SystemClock
from app.config import Settings, get_settings
from app.db import create_engine, create_session_factory
from app.health.api import router as health_router
from app.users.api import router as users_router


async def _handle_invalid_credentials(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Incorrect email or password"},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _handle_invalid_refresh_token(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid refresh token"},
    )


def create_app(
    settings: Settings | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application instance."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or get_settings()
        engine = create_engine(resolved_settings.database_url)
        session_factory = create_session_factory(engine)

        application.state.settings = resolved_settings
        application.state.clock = clock or SystemClock()
        application.state.password_hasher = PasswordHasher()
        application.state.engine = engine
        application.state.session_factory = session_factory

        try:
            yield
        finally:
            await engine.dispose()

    application = FastAPI(title="FastAPI Starter Kit", lifespan=lifespan)
    application.add_exception_handler(InvalidCredentials, _handle_invalid_credentials)
    application.add_exception_handler(InvalidRefreshToken, _handle_invalid_refresh_token)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    return application


app = create_app()
