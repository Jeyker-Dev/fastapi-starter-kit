from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import PasswordHasher
from app.auth.repository import SqlAlchemyRefreshTokenRepository
from app.auth.service import AuthService
from app.auth.tokens import TokenIssuer
from app.clock import Clock
from app.config import Settings
from app.db import get_session
from app.users.domain import User
from app.users.repository import SqlAlchemyUserRepository
from app.users.service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def _build_user_service(request: Request, session: AsyncSession) -> UserService:
    clock: Clock = request.app.state.clock
    hasher: PasswordHasher = request.app.state.password_hasher
    return UserService(
        users=SqlAlchemyUserRepository(session),
        hasher=hasher,
        clock=clock,
    )


def _build_token_issuer(request: Request) -> TokenIssuer:
    settings: Settings = request.app.state.settings
    clock: Clock = request.app.state.clock
    return TokenIssuer(
        secret=settings.jwt_secret.get_secret_value(),
        access_token_ttl_minutes=settings.access_token_ttl_minutes,
        refresh_token_ttl_days=settings.refresh_token_ttl_days,
        clock=clock,
    )


def get_auth_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    """Build AuthService with request-scoped repositories and app singletons."""
    hasher: PasswordHasher = request.app.state.password_hasher
    return AuthService(
        users=_build_user_service(request, session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        passwords=hasher,
        tokens=_build_token_issuer(request),
    )


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Authenticate and load the active user from a Bearer access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    user_id = _build_token_issuer(request).decode_access_token(token)
    if user_id is None:
        raise credentials_exception

    user = await _build_user_service(request, session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user
