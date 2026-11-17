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


class SqlAlchemyRefreshTokenRepository:
    """SQLAlchemy implementation of RefreshTokenRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            id=token.id,
            user_id=token.user_id,
            family_id=token.family_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            created_at=token.created_at,
        )
        self._session.add(model)
        await self._session.commit()
        return _to_domain(model)
