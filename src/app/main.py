from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.db import create_engine, create_session_factory
from app.health.api import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or get_settings()
        engine = create_engine(resolved_settings.database_url)
        session_factory = create_session_factory(engine)

        application.state.settings = resolved_settings
        application.state.engine = engine
        application.state.session_factory = session_factory

        try:
            yield
        finally:
            await engine.dispose()

    application = FastAPI(title="FastAPI Starter Kit", lifespan=lifespan)
    application.include_router(health_router)
    return application


app = create_app()
