from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserResponse(BaseModel):
    """Public HTTP representation of a user without password_hash."""

    id: UUID
    email: str
    is_active: bool
    created_at: datetime
