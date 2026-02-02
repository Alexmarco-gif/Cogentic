"""
Organization management endpoints.

Handles organization CRUD operations and member management.
"""

from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import (
    get_current_user,
    AuthContext,
    require_admin,
    require_owner,
    require_can_manage_member,
)
from backend.auth.guards import can_manage_member
from backend.database import get_db
from backend.repositories.organization import OrganizationRepository
from backend.models.organization import Organization

router = APIRouter(prefix="/orgs")


# Pydantic schemas
class OrganizationResponse(BaseModel):
    """Organization response model"""

    id: str
    name: str
    slug: str
    created_at: str

    class Config:
        from_attributes = True


class OrganizationUpdate(BaseModel):
    """Organization update request"""

    name: str | None = Field(None, min_length=1, max_length=100)
    slug: str | None = Field(None, min_length=2, max_length=50, pattern="^[a-z0-9-]+$")


class MemberResponse(BaseModel):
    """Organization member response"""

    user_id: str
    role: str
    status: str
    joined_at: str

    class Config:
        from_attributes = True


class MemberRoleUpdate(BaseModel):
    """Update member role request"""

    role: str = Field(..., pattern="^(viewer|member|admin|owner)$")


class AddMemberRequest(BaseModel):
    """Add member to organization request"""

    user_id: str
    role: str = Field(default="member", pattern="^(viewer|member|admin|owner)$")


@router.get("/{org_id}")
async def get_organization(
    org_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """
    Get organization details.

    User must be a member of the organization.
    """
    # Verify user is member of this org
    if auth.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    repo = OrganizationRepository(db, user_id=auth.user_id, request_id=None)
    org = await repo.get(org_id)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        created_at=org.created_at.isoformat(),
    )


@router.patch("/{org_id}")
async def update_organization(
    org_id: UUID,
    updates: OrganizationUpdate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """
    Update organization details.

    Requires admin or owner role.
    """
    require_admin(auth)

    if auth.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    repo = OrganizationRepository(db, user_id=auth.user_id, request_id=None)

    # Build update dict (only include non-None values)
    update_data = {}
    if updates.name is not None:
        update_data["name"] = updates.name
    if updates.slug is not None:
        # Check if slug is already taken
        if await repo.slug_exists(updates.slug):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Slug already taken"
            )
        update_data["slug"] = updates.slug

    org = await repo.update(org_id, **update_data)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    await db.commit()

    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        created_at=org.created_at.isoformat(),
    )


@router.get("/{org_id}/members")
async def list_members(
    org_id: UUID,
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    List organization members.

    Optional role filter: viewer, member, admin, owner
    """
    if auth.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    repo = OrganizationRepository(db, user_id=auth.user_id, request_id=None)
    members = await repo.list_members(org_id, skip=skip, limit=limit, role_filter=role)
    total = await repo.count_members(org_id, role_filter=role)

    return {
        "members": [
            MemberResponse(
                user_id=str(m.user_id),
                role=m.role,
                status=m.status,
                joined_at=m.created_at.isoformat(),
            )
            for m in members
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("/{org_id}/members")
async def add_member(
    org_id: UUID,
    request: AddMemberRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    """
    Add a new member to the organization.

    Requires admin or owner role.
    Admins can only add members/viewers, not admins/owners.
    """
    require_admin(auth)

    if auth.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    # Check if requester can assign this role
    if not can_manage_member(auth, request.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot assign role '{request.role}' with your current role '{auth.role}'",
        )

    repo = OrganizationRepository(db, user_id=auth.user_id, request_id=None)

    # Check if user is already a member
    existing = await repo.get_user_membership(org_id, UUID(request.user_id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already a member"
        )

    membership = await repo.add_member(org_id, UUID(request.user_id), request.role)
    await db.commit()

    return MemberResponse(
        user_id=str(membership.user_id),
        role=membership.role,
        status=membership.status,
        joined_at=membership.created_at.isoformat(),
    )


@router.patch("/{org_id}/members/{user_id}")
async def update_member_role(
    org_id: UUID,
    user_id: UUID,
    request: MemberRoleUpdate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    """
    Update a member's role.

    Requires permission to manage the target role.
    Owners can manage all roles, admins can manage members/viewers.
    """
    require_admin(auth)
    require_can_manage_member(auth, request.role)

    if auth.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    repo = OrganizationRepository(db, user_id=auth.user_id, request_id=None)
    membership = await repo.update_member_role(org_id, user_id, request.role)

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    await db.commit()

    return MemberResponse(
        user_id=str(membership.user_id),
        role=membership.role,
        status=membership.status,
        joined_at=membership.created_at.isoformat(),
    )


@router.delete("/{org_id}/members/{user_id}")
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Remove a member from the organization.

    Requires admin or owner role.
    Cannot remove the last owner.
    """
    require_admin(auth)

    if auth.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    # Prevent removing self
    if user_id == auth.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the organization",
        )

    repo = OrganizationRepository(db, user_id=auth.user_id, request_id=None)

    # Get member to check their role
    membership = await repo.get_user_membership(org_id, user_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    # Check if requester can remove this member
    require_can_manage_member(auth, membership.role)

    # If removing an owner, ensure there's at least one other owner
    if membership.role == "owner":
        owner_count = await repo.count_members(org_id, role_filter="owner")
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner",
            )

    success = await repo.remove_member(org_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    await db.commit()

    return {"message": "Member removed successfully"}


@router.delete("/{org_id}")
async def delete_organization(
    org_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Delete an organization (soft delete).

    Requires owner role.
    This is a destructive operation and cannot be undone.
    """
    require_owner(auth)

    if auth.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    repo = OrganizationRepository(db, user_id=auth.user_id, request_id=None)
    org = await repo.soft_delete(org_id)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    await db.commit()

    return {"message": "Organization deleted successfully"}
