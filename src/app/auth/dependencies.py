from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import PasswordHasher
from app.auth.repository import SqlAlchemyRefreshTokenRepository
from app.auth.service import AuthService
from app.auth.tokens import TokenIssuer
from app.clock import Clock
from app.config import Settings
from app.db import get_session
from app.users.repository import SqlAlchemyUserRepository
from app.users.service import UserService


def get_auth_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    """Build AuthService with request-scoped repositories and app singletons."""
    settings: Settings = request.app.state.settings
    clock: Clock = request.app.state.clock
    hasher: PasswordHasher = request.app.state.password_hasher

    user_service = UserService(
        users=SqlAlchemyUserRepository(session),
        hasher=hasher,
        clock=clock,
    )
    token_issuer = TokenIssuer(
        secret=settings.jwt_secret.get_secret_value(),
        access_token_ttl_minutes=settings.access_token_ttl_minutes,
        refresh_token_ttl_days=settings.refresh_token_ttl_days,
        clock=clock,
    )
    return AuthService(
        users=user_service,
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        passwords=hasher,
        tokens=token_issuer,
    )
