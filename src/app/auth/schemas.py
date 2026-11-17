from pydantic import BaseModel


class TokenResponse(BaseModel):
    """HTTP response payload containing issued access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
