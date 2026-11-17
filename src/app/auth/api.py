from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import get_auth_service
from app.auth.domain import TokenPair
from app.auth.schemas import RefreshRequest, TokenResponse
from app.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_token_response(pair: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


@router.post("/token", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate with OAuth2 password form credentials and issue tokens."""
    pair = await auth_service.login(
        email=form_data.username,
        password=form_data.password,
    )
    return _to_token_response(pair)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Rotate a valid refresh token and issue a new token pair."""
    pair = await auth_service.refresh(body.refresh_token)
    return _to_token_response(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """Revoke the refresh token session family idempotently."""
    await auth_service.logout(body.refresh_token)
