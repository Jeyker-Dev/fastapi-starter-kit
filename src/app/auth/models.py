from datetime import datetime
from uuid import UUID

from sqlalchemy import CHAR, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RefreshTokenModel(Base):
    """SQLAlchemy model for the refresh_tokens table."""

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    family_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
