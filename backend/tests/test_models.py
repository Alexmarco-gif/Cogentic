"""Test database models and connections"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, Organization, User, OrgUser


@pytest_asyncio.fixture
async def db_session():
    """Create test database session"""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_organization(db_session):
    """Test organization creation"""
    org = Organization(
        name="Test Org",
        slug="test-org",
        billing_email="billing@test.com",
    )

    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    assert org.id is not None
    assert org.slug == "test-org"
    assert org.max_users == 10  # Default


@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test user creation"""
    user = User(
        auth0_id="auth0|12345",
        email="test@example.com",
        name="Test User",
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.login_count == 0  # Default


@pytest.mark.asyncio
async def test_org_user_membership(db_session):
    """Test organization-user relationship"""
    # Create org and user
    org = Organization(name="Test Org", slug="test-org")
    user = User(auth0_id="auth0|12345", email="test@example.com")

    db_session.add(org)
    db_session.add(user)
    await db_session.commit()

    # Create membership
    membership = OrgUser(
        org_id=org.id,
        user_id=user.id,
        role="owner",
    )

    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(membership)

    assert membership.id is not None
    assert membership.role == "owner"
    assert membership.status == "active"  # Default
