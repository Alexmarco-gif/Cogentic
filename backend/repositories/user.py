"""User repository"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.user import User
from backend.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for user operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_auth0_id(self, auth0_id: str) -> User | None:
        """Get user by Auth0 ID"""
        result = await self.db.execute(select(User).where(User.auth0_id == auth0_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_with_organizations(self, user_id: UUID) -> User | None:
        """Get user with their organization memberships"""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.organizations))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update_from_auth0(
        self,
        auth0_id: str,
        email: str,
        name: str | None = None,
        picture_url: str | None = None,
    ) -> User:
        """Create or update user from Auth0 data"""
        user = await self.get_by_auth0_id(auth0_id)

        if user:
            # Update existing user
            user.email = email
            user.name = name or user.name
            user.picture_url = picture_url or user.picture_url
            await self.db.flush()
            await self.db.refresh(user)
        else:
            # Create new user
            user = await self.create(
                auth0_id=auth0_id,
                email=email,
                name=name,
                picture_url=picture_url,
            )

        return user
