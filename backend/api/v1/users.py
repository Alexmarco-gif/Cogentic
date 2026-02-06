"""
User profile endpoints.

Handles user profile retrieval and updates.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import AuthContext, get_current_user
from backend.database import get_db
from backend.repositories.user import UserRepository

router = APIRouter(prefix="/users")


class UserProfileResponse(BaseModel):
    """User profile response model"""

    id: str
    auth0_id: str
    email: str
    name: str | None
    picture_url: str | None
    created_at: str
    last_login_at: str | None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User profile update request"""

    name: str | None = Field(None, min_length=1, max_length=100)
    picture_url: str | None = None


@router.get("/me")
async def get_my_profile(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """
    Get current user's profile.

    Returns complete user profile information.
    """
    repo = UserRepository(db)
    user = await repo.get(auth.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserProfileResponse(
        id=str(user.id),
        auth0_id=user.auth0_id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.patch("/me")
async def update_my_profile(
    updates: UserProfileUpdate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """
    Update current user's profile.

    Users can only update their own profile.
    """
    repo = UserRepository(db)

    # Build update dict
    update_data = {}
    if updates.name is not None:
        update_data["name"] = updates.name
    if updates.picture_url is not None:
        update_data["picture_url"] = updates.picture_url

    user = await repo.update(auth.user_id, **update_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    await db.commit()

    return UserProfileResponse(
        id=str(user.id),
        auth0_id=user.auth0_id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.get("/{user_id}")
async def get_user_profile(
    user_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """
    Get another user's profile (public info only).

    Only available to authenticated users.
    Returns limited public information.
    """
    repo = UserRepository(db)
    user = await repo.get(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Return public profile only
    return UserProfileResponse(
        id=str(user.id),
        auth0_id=user.auth0_id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        created_at=user.created_at.isoformat(),
        last_login_at=None,  # Don't expose last login for other users
    )
