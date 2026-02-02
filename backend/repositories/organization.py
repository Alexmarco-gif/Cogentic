"""Organization repository"""

import time
from uuid import UUID

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.organization import Organization
from backend.models.org_user import OrgUser
from backend.repositories.base import BaseRepository
from backend.repositories.audit import audit_logger


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for organization operations with audit logging"""

    def __init__(
        self,
        db: AsyncSession,
        user_id: UUID | None = None,
        request_id: str | None = None,
    ):
        super().__init__(Organization, db)
        self.user_id = user_id
        self.request_id = request_id

    async def get_by_slug(self, slug: str) -> Organization | None:
        """Get organization by slug"""
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        """Check if slug is already taken"""
        org = await self.get_by_slug(slug)
        return org is not None

    async def get_user_membership(self, org_id: UUID, user_id: UUID) -> OrgUser | None:
        """
        Get user's membership in organization with audit logging.

        Args:
            org_id: Organization ID
            user_id: User ID

        Returns:
            OrgUser membership record or None if not a member
        """
        start_time = time.time()

        result = await self.db.execute(
            select(OrgUser)
            .where(OrgUser.org_id == org_id)
            .where(OrgUser.user_id == user_id)
            .where(OrgUser.status == "active")
        )
        membership = result.scalar_one_or_none()

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=org_id,
            table="org_users",
            action="get_membership",
            filters={"user_id": user_id, "org_id": org_id},
            result_count=1 if membership else 0,
            duration_ms=duration_ms,
            request_id=self.request_id,
        )

        return membership

    async def list_members(
        self,
        org_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        role_filter: str | None = None,
    ) -> list[OrgUser]:
        """
        List all members of an organization with optional role filtering.

        Args:
            org_id: Organization ID
            skip: Pagination offset
            limit: Max results
            role_filter: Optional role filter (e.g., "admin", "member")

        Returns:
            List of OrgUser membership records
        """
        start_time = time.time()

        query = (
            select(OrgUser)
            .where(OrgUser.org_id == org_id)
            .where(OrgUser.status == "active")
        )

        if role_filter:
            query = query.where(OrgUser.role == role_filter)

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        members = list(result.scalars().all())

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=org_id,
            table="org_users",
            action="list_members",
            filters={"role": role_filter} if role_filter else {},
            result_count=len(members),
            duration_ms=duration_ms,
            request_id=self.request_id,
        )

        return members

    async def count_members(self, org_id: UUID, role_filter: str | None = None) -> int:
        """
        Count members in organization.

        Args:
            org_id: Organization ID
            role_filter: Optional role filter

        Returns:
            Total member count
        """
        query = (
            select(func.count(OrgUser.id))
            .where(OrgUser.org_id == org_id)
            .where(OrgUser.status == "active")
        )

        if role_filter:
            query = query.where(OrgUser.role == role_filter)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def update_member_role(
        self, org_id: UUID, user_id: UUID, new_role: str
    ) -> OrgUser | None:
        """
        Update a member's role in organization.

        Args:
            org_id: Organization ID
            user_id: User ID
            new_role: New role (owner, admin, member, viewer)

        Returns:
            Updated OrgUser or None if not found
        """
        start_time = time.time()

        membership = await self.get_user_membership(org_id, user_id)
        if not membership:
            return None

        old_role = membership.role
        membership.role = new_role
        await self.db.flush()
        await self.db.refresh(membership)

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=org_id,
            table="org_users",
            action="update_member_role",
            filters={"user_id": user_id, "old_role": old_role, "new_role": new_role},
            result_count=1,
            duration_ms=duration_ms,
            request_id=self.request_id,
        )

        return membership

    async def remove_member(self, org_id: UUID, user_id: UUID) -> bool:
        """
        Remove a member from organization (soft delete).

        Args:
            org_id: Organization ID
            user_id: User ID to remove

        Returns:
            True if removed, False if not found
        """
        start_time = time.time()

        membership = await self.get_user_membership(org_id, user_id)
        if not membership:
            return False

        membership.status = "removed"
        await self.db.flush()

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=org_id,
            table="org_users",
            action="remove_member",
            filters={"user_id": user_id},
            result_count=1,
            duration_ms=duration_ms,
            request_id=self.request_id,
        )

        return True

    async def add_member(
        self, org_id: UUID, user_id: UUID, role: str = "member"
    ) -> OrgUser:
        """
        Add a new member to organization.

        Args:
            org_id: Organization ID
            user_id: User ID to add
            role: Initial role (default: member)

        Returns:
            Created OrgUser membership
        """
        start_time = time.time()

        membership = OrgUser(org_id=org_id, user_id=user_id, role=role, status="active")
        self.db.add(membership)
        await self.db.flush()
        await self.db.refresh(membership)

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=org_id,
            table="org_users",
            action="add_member",
            filters={"user_id": user_id, "role": role},
            result_count=1,
            duration_ms=duration_ms,
            request_id=self.request_id,
        )

        return membership
