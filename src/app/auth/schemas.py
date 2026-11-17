from pydantic import BaseModel


class RefreshRequest(BaseModel):
    """HTTP request payload containing an opaque refresh token."""

    refresh_token: str


class TokenResponse(BaseModel):
    """HTTP response payload containing issued access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
