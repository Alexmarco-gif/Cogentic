"""
Repository layer tests.

Covers:
  - BaseRepository: CRUD, bulk operations, pagination, filtering, soft delete
  - TenantRepository: org scoping, cross-org isolation, audit logging, verify_org_access
  - UserRepository: get_by_auth0_id, get_by_email, create_or_update_from_auth0
  - OrganizationRepository: slug lookup, membership CRUD, role updates
  - SignalRepository: org scoping, contract/type/entity filtering, trending, feed
  - SignalContractRepository: active/degraded listing, mark_fetched, mark_failed
  - ChatSessionRepository: user sessions, messages, archiving
  - DocumentRepository: owner filtering, status filtering, storage calculation
  - IntelligenceBriefRepository: published listing, stale briefs, mark_refreshed
  - CreditRepository: consume, balance, overage, reset
  - APIKeyRepository: key generation, hash lookup, revocation, counting
  - EntityRepository: name/type/industry filters, signal count
  - IndustryRepository: slug, tree hierarchy
  - FeatureGateRepository: feature key lookup, tier filtering, enterprise-only
  - RecommendationRepository: upsert, source lookup, active listing
  - SignalScoreRepository: upsert, signal/model lookups
"""

from uuid import uuid4

import pytest

from backend.models import (
    Document,
    Industry,
    User,
)
from backend.repositories.api_key import APIKeyRepository
from backend.repositories.audit import audit_logger
from backend.repositories.base import BaseRepository, TenantRepository
from backend.repositories.chat_session import ChatSessionRepository
from backend.repositories.document import DocumentRepository
from backend.repositories.entity import EntityRepository
from backend.repositories.feature_gate_repository import FeatureGateRepository
from backend.repositories.industry import IndustryRepository
from backend.repositories.intelligence_brief import IntelligenceBriefRepository
from backend.repositories.organization import OrganizationRepository
from backend.repositories.recommendation import RecommendationRepository
from backend.repositories.signal import SignalRepository
from backend.repositories.signal_contract import SignalContractRepository
from backend.repositories.signal_score import SignalScoreRepository
from backend.repositories.user import UserRepository
from tests.conftest import (
    create_api_key,
    create_chat_message,
    create_chat_session,
    create_document,
    create_entity,
    create_feature_gate,
    create_industry,
    create_intelligence_brief,
    create_org_user,
    create_organization,
    create_signal,
    create_signal_contract,
    create_user,
)

pytestmark = pytest.mark.asyncio


# ══════════════════════════════════════════════════════════════════════
#  BaseRepository
# ══════════════════════════════════════════════════════════════════════


class TestBaseRepository:
    async def test_create_and_get(self, db_session):
        repo = BaseRepository(User, db_session)
        user = await repo.create(
            id=uuid4(),
            auth0_id=f"auth0|{uuid4().hex[:24]}",
            email="base-repo@test.com",
            name="Base Repo User",
        )
        assert user.id is not None
        fetched = await repo.get(user.id)
        assert fetched is not None
        assert fetched.email == "base-repo@test.com"

    async def test_get_nonexistent(self, db_session):
        repo = BaseRepository(User, db_session)
        result = await repo.get(uuid4())
        assert result is None

    async def test_get_by_ids(self, db_session):
        repo = BaseRepository(Industry, db_session)
        i1 = await repo.create(id=uuid4(), name="Ind1", slug=f"ind-{uuid4().hex[:8]}")
        i2 = await repo.create(id=uuid4(), name="Ind2", slug=f"ind-{uuid4().hex[:8]}")
        results = await repo.get_by_ids([i1.id, i2.id])
        assert len(results) == 2

    async def test_get_by_ids_empty(self, db_session):
        repo = BaseRepository(Industry, db_session)
        results = await repo.get_by_ids([])
        assert results == []

    async def test_get_multi_with_pagination(self, db_session):
        repo = BaseRepository(Industry, db_session)
        for i in range(5):
            await repo.create(
                id=uuid4(), name=f"Multi-{i}", slug=f"multi-{uuid4().hex[:8]}"
            )
        page1 = await repo.get_multi(skip=0, limit=2)
        page2 = await repo.get_multi(skip=2, limit=2)
        assert len(page1) == 2
        assert len(page2) == 2

    async def test_get_multi_with_filters(self, db_session):
        repo = BaseRepository(Industry, db_session)
        slug = f"filter-{uuid4().hex[:8]}"
        await repo.create(id=uuid4(), name="Filterable", slug=slug)
        await repo.create(id=uuid4(), name="Other", slug=f"other-{uuid4().hex[:8]}")
        results = await repo.get_multi(filters={"slug": slug})
        assert len(results) == 1
        assert results[0].slug == slug

    async def test_count(self, db_session):
        repo = BaseRepository(Industry, db_session)
        slug = f"count-{uuid4().hex[:8]}"
        await repo.create(id=uuid4(), name="Count1", slug=slug)
        count = await repo.count(filters={"slug": slug})
        assert count == 1

    async def test_update(self, db_session):
        repo = BaseRepository(User, db_session)
        user = await repo.create(
            id=uuid4(),
            auth0_id=f"auth0|{uuid4().hex[:24]}",
            email="update-repo@test.com",
            name="Before",
        )
        updated = await repo.update(user.id, name="After")
        assert updated.name == "After"

    async def test_update_nonexistent(self, db_session):
        repo = BaseRepository(User, db_session)
        result = await repo.update(uuid4(), name="No one")
        assert result is None

    async def test_create_many(self, db_session):
        repo = BaseRepository(Industry, db_session)
        items = [
            {"id": uuid4(), "name": f"Bulk-{i}", "slug": f"bulk-{uuid4().hex[:8]}"}
            for i in range(3)
        ]
        created = await repo.create_many(items)
        assert len(created) == 3

    async def test_create_many_empty(self, db_session):
        repo = BaseRepository(Industry, db_session)
        created = await repo.create_many([])
        assert created == []

    async def test_update_many(self, db_session):
        repo = BaseRepository(Industry, db_session)
        i1 = await repo.create(id=uuid4(), name="UM1", slug=f"um-{uuid4().hex[:8]}")
        i2 = await repo.create(id=uuid4(), name="UM2", slug=f"um-{uuid4().hex[:8]}")
        count = await repo.update_many(
            [
                {"id": i1.id, "name": "Updated1"},
                {"id": i2.id, "name": "Updated2"},
            ]
        )
        assert count == 2

    async def test_update_many_empty(self, db_session):
        repo = BaseRepository(Industry, db_session)
        count = await repo.update_many([])
        assert count == 0

    async def test_delete(self, db_session):
        repo = BaseRepository(Industry, db_session)
        ind = await repo.create(
            id=uuid4(), name="Delete Me", slug=f"del-{uuid4().hex[:8]}"
        )
        deleted = await repo.delete(ind.id)
        assert deleted is True
        assert await repo.get(ind.id) is None

    async def test_delete_nonexistent(self, db_session):
        repo = BaseRepository(Industry, db_session)
        deleted = await repo.delete(uuid4())
        assert deleted is False

    async def test_delete_many(self, db_session):
        repo = BaseRepository(Industry, db_session)
        ids = []
        for i in range(3):
            ind = await repo.create(
                id=uuid4(), name=f"DM-{i}", slug=f"dm-{uuid4().hex[:8]}"
            )
            ids.append(ind.id)
        count = await repo.delete_many(ids)
        assert count == 3

    async def test_delete_many_empty(self, db_session):
        repo = BaseRepository(Industry, db_session)
        count = await repo.delete_many([])
        assert count == 0

    async def test_soft_delete(self, db_session):
        user = await create_user(db_session, email="soft-del@test.com")
        repo = BaseRepository(User, db_session)
        result = await repo.soft_delete(user.id)
        assert result is not None
        assert result.deleted_at is not None

    async def test_soft_delete_nonexistent(self, db_session):
        repo = BaseRepository(User, db_session)
        result = await repo.soft_delete(uuid4())
        assert result is None

    async def test_exists(self, db_session):
        user = await create_user(db_session)
        repo = BaseRepository(User, db_session)
        assert await repo.exists(user.id) is True
        assert await repo.exists(uuid4()) is False


# ══════════════════════════════════════════════════════════════════════
#  TenantRepository
# ══════════════════════════════════════════════════════════════════════


class TestTenantRepository:
    async def test_create_auto_injects_org_id(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        repo = TenantRepository(Document, db_session, org_id=org.id, user_id=user.id)
        doc = await repo.create(
            id=uuid4(),
            filename="auto.pdf",
            size_bytes=100,
            owner_id=user.id,
        )
        assert doc.org_id == org.id

    async def test_get_scoped_to_org(self, db_session):
        org_a = await create_organization(db_session, slug="tenant-a")
        org_b = await create_organization(db_session, slug="tenant-b")
        user = await create_user(db_session)
        doc = await create_document(
            db_session, org=org_a, user=user, filename="scoped.pdf"
        )

        repo_a = TenantRepository(Document, db_session, org_id=org_a.id)
        repo_b = TenantRepository(Document, db_session, org_id=org_b.id)

        assert await repo_a.get(doc.id) is not None
        assert await repo_b.get(doc.id) is None  # Cross-org blocked

    async def test_get_multi_scoped(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_document(db_session, org=org, user=user, filename="a.pdf")
        await create_document(db_session, org=org, user=user, filename="b.pdf")

        other_org = await create_organization(db_session)
        await create_document(db_session, org=other_org, user=user, filename="c.pdf")

        repo = TenantRepository(Document, db_session, org_id=org.id)
        docs = await repo.get_multi()
        assert len(docs) == 2

    async def test_count_scoped(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_document(db_session, org=org, user=user)
        repo = TenantRepository(Document, db_session, org_id=org.id)
        assert await repo.count() == 1

    async def test_update_prevents_org_id_hijack(self, db_session):
        org = await create_organization(db_session)
        other_org = await create_organization(db_session)
        user = await create_user(db_session)
        doc = await create_document(db_session, org=org, user=user)

        repo = TenantRepository(Document, db_session, org_id=org.id)
        updated = await repo.update(doc.id, org_id=other_org.id, filename="hijack.pdf")
        assert updated.org_id == org.id  # org_id NOT changed
        assert updated.filename == "hijack.pdf"

    async def test_delete_scoped(self, db_session):
        org_a = await create_organization(db_session, slug="del-a")
        org_b = await create_organization(db_session, slug="del-b")
        user = await create_user(db_session)
        doc = await create_document(db_session, org=org_a, user=user)

        repo_b = TenantRepository(Document, db_session, org_id=org_b.id)
        assert await repo_b.delete(doc.id) is False  # Cross-org blocked

        repo_a = TenantRepository(Document, db_session, org_id=org_a.id)
        assert await repo_a.delete(doc.id) is True

    async def test_exists_scoped(self, db_session):
        org = await create_organization(db_session)
        other_org = await create_organization(db_session)
        user = await create_user(db_session)
        doc = await create_document(db_session, org=org, user=user)

        repo = TenantRepository(Document, db_session, org_id=org.id)
        assert await repo.exists(doc.id) is True

        repo_other = TenantRepository(Document, db_session, org_id=other_org.id)
        assert await repo_other.exists(doc.id) is False

    async def test_verify_org_access(self, db_session):
        org = await create_organization(db_session)
        other_org = await create_organization(db_session)
        user = await create_user(db_session)
        doc = await create_document(db_session, org=org, user=user)

        repo = TenantRepository(Document, db_session, org_id=org.id)
        assert await repo.verify_org_access(doc.id) is True

        repo_other = TenantRepository(Document, db_session, org_id=other_org.id)
        assert await repo_other.verify_org_access(doc.id) is False

    async def test_verify_org_access_nonexistent(self, db_session):
        org = await create_organization(db_session)
        repo = TenantRepository(Document, db_session, org_id=org.id)
        assert await repo.verify_org_access(uuid4()) is False

    async def test_list_by_owner(self, db_session):
        org = await create_organization(db_session)
        user_a = await create_user(db_session, email="owner-a@test.com")
        user_b = await create_user(db_session, email="owner-b@test.com")
        await create_document(db_session, org=org, user=user_a, filename="a.pdf")
        await create_document(db_session, org=org, user=user_b, filename="b.pdf")

        repo = TenantRepository(Document, db_session, org_id=org.id)
        docs = await repo.list_by_owner(user_a.id)
        assert len(docs) == 1
        assert docs[0].filename == "a.pdf"


# ══════════════════════════════════════════════════════════════════════
#  UserRepository
# ══════════════════════════════════════════════════════════════════════


class TestUserRepository:
    async def test_get_by_auth0_id(self, db_session):
        auth0_id = f"auth0|{uuid4().hex[:24]}"
        await create_user(db_session, auth0_id=auth0_id, email="auth0@test.com")
        repo = UserRepository(db_session)
        user = await repo.get_by_auth0_id(auth0_id)
        assert user is not None
        assert user.email == "auth0@test.com"

    async def test_get_by_auth0_id_not_found(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.get_by_auth0_id("auth0|nonexistent") is None

    async def test_get_by_email(self, db_session):
        await create_user(db_session, email="find-me@test.com")
        repo = UserRepository(db_session)
        user = await repo.get_by_email("find-me@test.com")
        assert user is not None
        assert user.email == "find-me@test.com"

    async def test_get_by_email_not_found(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.get_by_email("ghost@test.com") is None

    async def test_create_or_update_from_auth0_new(self, db_session):
        repo = UserRepository(db_session)
        auth0_id = f"auth0|{uuid4().hex[:24]}"
        user = await repo.create_or_update_from_auth0(
            auth0_id=auth0_id, email="new@auth0.com", name="New User"
        )
        assert user.email == "new@auth0.com"
        assert user.auth0_id == auth0_id

    async def test_create_or_update_from_auth0_existing(self, db_session):
        auth0_id = f"auth0|{uuid4().hex[:24]}"
        await create_user(db_session, auth0_id=auth0_id, email="existing@auth0.com")
        repo = UserRepository(db_session)
        user = await repo.create_or_update_from_auth0(
            auth0_id=auth0_id, email="existing@auth0.com", name="Updated"
        )
        assert user.name == "Updated"


# ══════════════════════════════════════════════════════════════════════
#  OrganizationRepository
# ══════════════════════════════════════════════════════════════════════


class TestOrganizationRepository:
    async def test_get_by_slug(self, db_session):
        slug = f"org-slug-{uuid4().hex[:8]}"
        await create_organization(db_session, slug=slug, name="Slug Org")
        repo = OrganizationRepository(db_session)
        org = await repo.get_by_slug(slug)
        assert org is not None
        assert org.name == "Slug Org"

    async def test_slug_exists(self, db_session):
        slug = f"exists-{uuid4().hex[:8]}"
        await create_organization(db_session, slug=slug)
        repo = OrganizationRepository(db_session)
        assert await repo.slug_exists(slug) is True
        assert await repo.slug_exists("nonexistent-slug") is False

    async def test_add_member(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        repo = OrganizationRepository(db_session)
        membership = await repo.add_member(org.id, user.id, role="admin")
        assert membership.role == "admin"
        assert membership.org_id == org.id

    async def test_get_user_membership(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_org_user(db_session, org=org, user=user, role="member")
        repo = OrganizationRepository(db_session)
        mem = await repo.get_user_membership(org.id, user.id)
        assert mem is not None
        assert mem.role == "member"

    async def test_list_members(self, db_session):
        org = await create_organization(db_session)
        u1 = await create_user(db_session, email="m1@test.com")
        u2 = await create_user(db_session, email="m2@test.com")
        await create_org_user(db_session, org=org, user=u1, role="member")
        await create_org_user(db_session, org=org, user=u2, role="admin")
        repo = OrganizationRepository(db_session)
        members = await repo.list_members(org.id)
        assert len(members) == 2

    async def test_update_member_role(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_org_user(db_session, org=org, user=user, role="member")
        repo = OrganizationRepository(db_session)
        updated = await repo.update_member_role(org.id, user.id, "admin")
        assert updated.role == "admin"

    async def test_count_members(self, db_session):
        org = await create_organization(db_session)
        u1 = await create_user(db_session, email="cnt1@test.com")
        u2 = await create_user(db_session, email="cnt2@test.com")
        await create_org_user(db_session, org=org, user=u1)
        await create_org_user(db_session, org=org, user=u2)
        repo = OrganizationRepository(db_session)
        assert await repo.count_members(org.id) == 2


# ══════════════════════════════════════════════════════════════════════
#  SignalRepository
# ══════════════════════════════════════════════════════════════════════


class TestSignalRepository:
    async def test_get_by_contract(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        s1 = await create_signal(db_session, contract=sc, title="Sig1")
        s2 = await create_signal(db_session, contract=sc, title="Sig2")
        repo = SignalRepository(db_session)
        signals = await repo.get_by_contract(sc.id)
        assert len(signals) >= 2

    async def test_get_by_type(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        await create_signal(db_session, contract=sc, signal_type="regulatory")
        await create_signal(db_session, contract=sc, signal_type="news")
        repo = SignalRepository(db_session)
        regs = await repo.get_by_type("regulatory")
        assert all(s.signal_type == "regulatory" for s in regs)

    async def test_find_by_content_hash(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(db_session, contract=sc)
        sig.content_hash = "unique_hash_123"
        await db_session.flush()
        repo = SignalRepository(db_session)
        found = await repo.find_by_content_hash("unique_hash_123")
        assert found is not None
        assert found.id == sig.id

    async def test_count_by_contract(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        await create_signal(db_session, contract=sc)
        await create_signal(db_session, contract=sc)
        repo = SignalRepository(db_session)
        count = await repo.count_by_contract(sc.id)
        assert count >= 2

    async def test_get_visible(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        await create_signal(db_session, contract=sc, confidence=0.9)
        await create_signal(db_session, contract=sc, confidence=0.3)
        repo = SignalRepository(db_session)
        visible = await repo.get_visible()
        assert all(s.confidence >= 0.6 for s in visible)


# ══════════════════════════════════════════════════════════════════════
#  SignalContractRepository
# ══════════════════════════════════════════════════════════════════════


class TestSignalContractRepository:
    async def test_get_active_contracts(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        repo = SignalContractRepository(db_session)
        active = await repo.get_active_contracts()
        assert len(active) >= 1
        assert all(c.is_active for c in active)

    async def test_get_by_industry(self, db_session):
        ind = await create_industry(
            db_session, name="ContractInd", slug=f"ci-{uuid4().hex[:8]}"
        )
        await create_signal_contract(db_session, industry=ind, name="CI Contract")
        repo = SignalContractRepository(db_session)
        contracts = await repo.get_by_industry(ind.id)
        assert len(contracts) >= 1

    async def test_get_by_source_type(self, db_session):
        ind = await create_industry(db_session)
        await create_signal_contract(db_session, industry=ind, source_type="api")
        repo = SignalContractRepository(db_session)
        api_contracts = await repo.get_by_source_type("api")
        assert all(c.source_type == "api" for c in api_contracts)

    async def test_mark_fetched(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        repo = SignalContractRepository(db_session)
        updated = await repo.mark_fetched(sc.id)
        assert updated is not None
        assert updated.last_fetched_at is not None

    async def test_mark_failed(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        repo = SignalContractRepository(db_session)
        updated = await repo.mark_failed(sc.id, "Connection timeout")
        assert updated is not None
        assert updated.failure_count >= 1
        assert updated.last_error == "Connection timeout"


# ══════════════════════════════════════════════════════════════════════
#  ChatSessionRepository
# ══════════════════════════════════════════════════════════════════════


class TestChatSessionRepository:
    async def test_get_user_sessions(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_chat_session(db_session, user=user, org=org, title="Chat 1")
        await create_chat_session(db_session, user=user, org=org, title="Chat 2")
        repo = ChatSessionRepository(db_session, org_id=org.id, user_id=user.id)
        sessions = await repo.get_user_sessions(user.id)
        assert len(sessions) >= 2

    async def test_add_message(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        cs = await create_chat_session(db_session, user=user, org=org)
        repo = ChatSessionRepository(db_session, org_id=org.id, user_id=user.id)
        msg = await repo.add_message(cs.id, role="user", content="Hello!")
        assert msg.role == "user"
        assert msg.content == "Hello!"

    async def test_get_message_count(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        cs = await create_chat_session(db_session, user=user, org=org)
        await create_chat_message(db_session, session=cs, content="Msg 1")
        await create_chat_message(db_session, session=cs, content="Msg 2")
        repo = ChatSessionRepository(db_session, org_id=org.id, user_id=user.id)
        count = await repo.get_message_count(cs.id)
        assert count == 2

    async def test_archive_session(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        cs = await create_chat_session(db_session, user=user, org=org)
        repo = ChatSessionRepository(db_session, org_id=org.id, user_id=user.id)
        archived = await repo.archive_session(cs.id)
        assert archived.status == "archived"


# ══════════════════════════════════════════════════════════════════════
#  DocumentRepository
# ══════════════════════════════════════════════════════════════════════


class TestDocumentRepository:
    async def test_get_by_owner(self, db_session):
        org = await create_organization(db_session)
        owner = await create_user(db_session, email="doc-owner@test.com")
        other = await create_user(db_session, email="doc-other@test.com")
        await create_document(db_session, org=org, user=owner, filename="mine.pdf")
        await create_document(db_session, org=org, user=other, filename="theirs.pdf")
        repo = DocumentRepository(db_session, org_id=org.id)
        docs = await repo.get_by_owner(owner.id)
        assert len(docs) == 1
        assert docs[0].filename == "mine.pdf"

    async def test_get_by_status(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_document(db_session, org=org, user=user)  # default: pending
        repo = DocumentRepository(db_session, org_id=org.id)
        pending = await repo.get_by_status("pending")
        assert len(pending) >= 1

    async def test_get_total_storage_bytes(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_document(db_session, org=org, user=user, size_bytes=500)
        await create_document(db_session, org=org, user=user, size_bytes=300)
        repo = DocumentRepository(db_session, org_id=org.id)
        total = await repo.get_total_storage_bytes()
        assert total >= 800


# ══════════════════════════════════════════════════════════════════════
#  IntelligenceBriefRepository
# ══════════════════════════════════════════════════════════════════════


class TestIntelligenceBriefRepository:
    async def test_get_published(self, db_session):
        org = await create_organization(db_session)
        ind = await create_industry(db_session)
        await create_intelligence_brief(
            db_session, industry=ind, org=org, status="published"
        )
        await create_intelligence_brief(
            db_session, industry=ind, org=org, status="draft"
        )
        repo = IntelligenceBriefRepository(db_session, org_id=org.id)
        published = await repo.get_published()
        assert all(b.status == "published" for b in published)

    async def test_get_by_industry(self, db_session):
        org = await create_organization(db_session)
        ind = await create_industry(
            db_session, name="BriefInd", slug=f"bi-{uuid4().hex[:8]}"
        )
        await create_intelligence_brief(db_session, industry=ind, org=org)
        repo = IntelligenceBriefRepository(db_session, org_id=org.id)
        briefs = await repo.get_by_industry(ind.id)
        assert len(briefs) >= 1

    async def test_mark_refreshed(self, db_session):
        org = await create_organization(db_session)
        ind = await create_industry(db_session)
        brief = await create_intelligence_brief(db_session, industry=ind, org=org)
        repo = IntelligenceBriefRepository(db_session, org_id=org.id)
        refreshed = await repo.mark_refreshed(brief.id)
        assert refreshed is not None


# ══════════════════════════════════════════════════════════════════════
#  EntityRepository
# ══════════════════════════════════════════════════════════════════════


class TestEntityRepository:
    async def test_get_by_name(self, db_session):
        await create_entity(db_session, name="UniqueEntity123")
        repo = EntityRepository(db_session)
        ent = await repo.get_by_name("UniqueEntity123")
        assert ent is not None
        assert ent.name == "UniqueEntity123"

    async def test_get_by_industry(self, db_session):
        ind = await create_industry(
            db_session, name="EntInd", slug=f"ei-{uuid4().hex[:8]}"
        )
        await create_entity(db_session, name="IndustryEnt", industry=ind)
        repo = EntityRepository(db_session)
        entities = await repo.get_by_industry(ind.id)
        assert len(entities) >= 1

    async def test_get_by_type(self, db_session):
        await create_entity(db_session, name="TypeEnt", entity_type="company")
        repo = EntityRepository(db_session)
        companies = await repo.get_by_type("company")
        assert all(e.entity_type == "company" for e in companies)


# ══════════════════════════════════════════════════════════════════════
#  IndustryRepository
# ══════════════════════════════════════════════════════════════════════


class TestIndustryRepository:
    async def test_get_by_slug(self, db_session):
        slug = f"ind-slug-{uuid4().hex[:8]}"
        await create_industry(db_session, name="SlugInd", slug=slug)
        repo = IndustryRepository(db_session)
        ind = await repo.get_by_slug(slug)
        assert ind is not None
        assert ind.name == "SlugInd"

    async def test_slug_exists(self, db_session):
        slug = f"exists-ind-{uuid4().hex[:8]}"
        await create_industry(db_session, slug=slug)
        repo = IndustryRepository(db_session)
        assert await repo.slug_exists(slug) is True
        assert await repo.slug_exists("nope") is False

    async def test_get_root_industries(self, db_session):
        await create_industry(db_session, name="Root", slug=f"root-{uuid4().hex[:8]}")
        repo = IndustryRepository(db_session)
        roots = await repo.get_root_industries()
        assert len(roots) >= 1


# ══════════════════════════════════════════════════════════════════════
#  FeatureGateRepository
# ══════════════════════════════════════════════════════════════════════


class TestFeatureGateRepository:
    async def test_get_by_feature_key(self, db_session):
        await create_feature_gate(db_session, feature_key="test_feature_key")
        repo = FeatureGateRepository(db_session)
        fg = await repo.get_by_feature_key("test_feature_key")
        assert fg is not None

    async def test_get_all_feature_gates(self, db_session):
        await create_feature_gate(db_session, feature_key=f"fg-{uuid4().hex[:8]}")
        repo = FeatureGateRepository(db_session)
        gates = await repo.get_all_feature_gates()
        assert len(gates) >= 1

    async def test_get_features_by_tier(self, db_session):
        await create_feature_gate(
            db_session, feature_key=f"tier-{uuid4().hex[:8]}", required_tier="growth"
        )
        repo = FeatureGateRepository(db_session)
        growth_features = await repo.get_features_by_tier("growth")
        assert all(f.required_tier == "growth" for f in growth_features)


# ══════════════════════════════════════════════════════════════════════
#  APIKeyRepository
# ══════════════════════════════════════════════════════════════════════


class TestAPIKeyRepository:
    async def test_generate_key_static(self):
        full_key, key_hash, prefix = APIKeyRepository.generate_key()
        assert full_key.startswith("cogent_pk_live_")
        assert len(key_hash) == 64  # SHA256 hex
        assert len(prefix) > 0

    async def test_hash_key_deterministic(self):
        h1 = APIKeyRepository.hash_key("my_secret_key")
        h2 = APIKeyRepository.hash_key("my_secret_key")
        assert h1 == h2

    async def test_create_key(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        repo = APIKeyRepository(db_session)
        api_key, plaintext = await repo.create_key(
            org_id=org.id,
            created_by_user_id=user.id,
            name="Test Key",
        )
        assert api_key.name == "Test Key"
        assert plaintext.startswith("cogent_pk_live_")

    async def test_list_by_org(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_api_key(db_session, org=org, user=user, name="Key1")
        await create_api_key(db_session, org=org, user=user, name="Key2")
        repo = APIKeyRepository(db_session)
        keys = await repo.list_by_org(org.id)
        assert len(keys) >= 2

    async def test_revoke_key(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        key = await create_api_key(db_session, org=org, user=user)
        repo = APIKeyRepository(db_session)
        revoked = await repo.revoke(key.id)
        assert revoked is not None
        assert revoked.revoked_at is not None

    async def test_count_active_by_org(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_api_key(db_session, org=org, user=user)
        repo = APIKeyRepository(db_session)
        count = await repo.count_active_by_org(org.id)
        assert count >= 1


# ══════════════════════════════════════════════════════════════════════
#  RecommendationRepository
# ══════════════════════════════════════════════════════════════════════


class TestRecommendationRepository:
    async def test_upsert_and_get(self, db_session):
        repo = RecommendationRepository(db_session)
        source_id = uuid4()
        target_id = uuid4()
        rec = await repo.upsert(
            source_type="signal",
            source_id=source_id,
            target_type="brief",
            target_id=target_id,
            score=0.9,
            reason="Related topics",
        )
        assert rec.score == 0.9

        results = await repo.get_for_source("signal", source_id)
        assert len(results) >= 1

    async def test_delete_for_source(self, db_session):
        repo = RecommendationRepository(db_session)
        source_id = uuid4()
        await repo.upsert(
            source_type="signal",
            source_id=source_id,
            target_type="brief",
            target_id=uuid4(),
            score=0.5,
            reason="Test",
        )
        count = await repo.delete_for_source("signal", source_id)
        assert count >= 1


# ══════════════════════════════════════════════════════════════════════
#  SignalScoreRepository
# ══════════════════════════════════════════════════════════════════════


class TestSignalScoreRepository:
    async def test_upsert_score(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(db_session, contract=sc)
        repo = SignalScoreRepository(db_session)
        score = await repo.upsert_score(sig.id, "relevance", 0.85)
        assert score.score_value == 0.85

    async def test_get_by_signal(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(db_session, contract=sc)
        repo = SignalScoreRepository(db_session)
        await repo.upsert_score(sig.id, "relevance", 0.8)
        await repo.upsert_score(sig.id, "impact", 0.6)
        scores = await repo.get_by_signal(sig.id)
        assert len(scores) >= 2


# ══════════════════════════════════════════════════════════════════════
#  Audit Logger
# ══════════════════════════════════════════════════════════════════════


class TestAuditLogger:
    def test_log_query_does_not_raise(self):
        audit_logger.log_query(
            user_id=uuid4(),
            org_id=uuid4(),
            table="test_table",
            action="read",
            filters={},
            result_count=5,
            duration_ms=10.0,
        )

    def test_log_cross_org_attempt_does_not_raise(self):
        audit_logger.log_cross_org_attempt(
            user_id=uuid4(),
            user_org_id=uuid4(),
            attempted_org_id=uuid4(),
            table="test_table",
            action="read",
            resource_id=uuid4(),
        )

    def test_log_missing_org_context(self):
        audit_logger.log_missing_org_context(
            table="test_table",
            action="read",
            user_id=uuid4(),
        )
