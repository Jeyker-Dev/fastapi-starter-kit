from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserModel(Base):
    """SQLAlchemy model for the users table."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
