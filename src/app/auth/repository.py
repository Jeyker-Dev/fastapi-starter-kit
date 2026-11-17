from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain import RefreshToken
from app.auth.models import RefreshTokenModel


def _to_domain(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=model.id,
        user_id=model.user_id,
        family_id=model.family_id,
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        revoked_at=model.revoked_at,
        created_at=model.created_at,
    )


def _to_model(token: RefreshToken) -> RefreshTokenModel:
    return RefreshTokenModel(
        id=token.id,
        user_id=token.user_id,
        family_id=token.family_id,
        token_hash=token.token_hash,
        expires_at=token.expires_at,
        revoked_at=token.revoked_at,
        created_at=token.created_at,
    )


class SqlAlchemyRefreshTokenRepository:
    """SQLAlchemy implementation of RefreshTokenRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> RefreshToken:
        model = _to_model(token)
        self._session.add(model)
        await self._session.commit()
        return _to_domain(model)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model is not None else None

    async def rotate(
        self,
        token_id: UUID,
        revoked_at: datetime,
        replacement: RefreshToken,
    ) -> bool:
        """Atomically revoke an active refresh token and insert its replacement."""
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.id == token_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
            .returning(RefreshTokenModel.id)
        )
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none() is None:
            await self._session.rollback()
            return False

        self._session.add(_to_model(replacement))
        await self._session.commit()
        return True

    async def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        """Revoke all active tokens belonging to a refresh token family."""
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.family_id == family_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        await self._session.execute(stmt)
        await self._session.commit()
