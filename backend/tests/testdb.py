import asyncio
from backend.database import get_db_context
from backend.models import Organization, User, OrgUser


async def test_database():
    async with get_db_context() as db:
        # Create an organization
        org = Organization(
            name="Test Company", slug="test-company", billing_email="billing@test.com"
        )
        db.add(org)
        await db.commit()
        print(f"✅ Created organization: {org.id}")

        # Create a user
        user = User(
            auth0_id="auth0|test123", email="test@example.com", name="Test User"
        )
        db.add(user)
        await db.commit()
        print(f"✅ Created user: {user.id}")

        # Create membership
        membership = OrgUser(org_id=org.id, user_id=user.id, role="owner")
        db.add(membership)
        await db.commit()
        print(f"✅ Created membership: {membership.id}")

        print("\n🎉 All database operations successful!")


# Run the test
asyncio.run(test_database())
exit()
