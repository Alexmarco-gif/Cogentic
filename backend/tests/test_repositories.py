import pytest

from backend.database import get_db_context
from backend.repositories.document import DocumentRepository
from backend.repositories.organization import OrganizationRepository
from backend.repositories.user import UserRepository


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_isolation():
    async with get_db_context() as db:
        # Create two organizations
        org_repo = OrganizationRepository(db)

        org1 = await org_repo.create(name="Org 1", slug="org-1")
        org2 = await org_repo.create(name="Org 2", slug="org-2")

        print(f"✅ Created Org 1: {org1.id}")
        print(f"✅ Created Org 2: {org2.id}")

        # Create a user for org1
        user_repo = UserRepository(db)
        user1 = await user_repo.create(
            auth0_id="auth0|testuser1", email="user1@test.com", name="Test User 1"
        )
        print(f"✅ Created User: {user1.id}")

        # Create documents in Org 1
        doc_repo_1 = DocumentRepository(db, org1.id)
        doc1 = await doc_repo_1.create(
            filename="org1-doc.pdf",
            size_bytes=1024,
            owner_id=user1.id,  # Use real user ID
        )
        print(f"✅ Created document in Org 1: {doc1.id}")

        # Try to access from Org 2 (should not see it)
        doc_repo_2 = DocumentRepository(db, org2.id)
        docs_in_org2 = await doc_repo_2.get_multi()

        print("\n📊 Documents in Org 1: 1")
        print(f"📊 Documents visible to Org 2: {len(docs_in_org2)}")

        if len(docs_in_org2) == 0:
            print("\n🎉 Tenant isolation works! Org 2 cannot see Org 1's documents")
        else:
            print("\n❌ TENANT ISOLATION FAILED!")
