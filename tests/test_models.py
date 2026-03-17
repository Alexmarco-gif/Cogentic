"""
Database / ORM model tests.

Covers:
  - CRUD operations on all core models
  - Relationship traversals
  - Unique constraints & FK cascades
  - Mixins (UUID, Timestamp, SoftDelete)
  - Data integrity checks
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.models import (
    Recommendation,
    SearchQuery,
    SignalEntity,
)
from tests.conftest import (
    create_chat_message,
    create_chat_session,
    create_credit_transaction,
    create_document,
    create_entity,
    create_feature_gate,
    create_industry,
    create_intelligence_brief,
    create_org_user,
    create_organization,
    create_signal,
    create_signal_contract,
    create_subscription,
    create_user,
)

pytestmark = pytest.mark.asyncio


# ── User model ───────────────────────────────────────────────────────


class TestUserModel:
    async def test_create_user(self, db_session):
        user = await create_user(db_session, email="alice@cogent.ai", name="Alice")
        assert user.id is not None
        assert user.email == "alice@cogent.ai"
        assert user.name == "Alice"
        assert user.auth0_id.startswith("auth0|")
        assert user.login_count == 0
        assert user.data_processing_consent is False

    async def test_user_has_timestamps(self, db_session):
        user = await create_user(db_session)
        assert user.created_at is not None
        assert user.updated_at is not None

    async def test_user_soft_delete(self, db_session):
        user = await create_user(db_session)
        assert user.is_deleted is False
        user.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()
        assert user.is_deleted is True

    async def test_user_unique_auth0_id(self, db_session):
        auth0_id = f"auth0|unique{uuid4().hex[:16]}"
        await create_user(db_session, auth0_id=auth0_id, email="a@test.com")
        with pytest.raises(Exception):  # IntegrityError
            async with db_session.begin_nested():
                await create_user(db_session, auth0_id=auth0_id, email="b@test.com")

    async def test_user_repr(self, db_session):
        user = await create_user(db_session, email="repr@cogent.ai")
        assert "repr@cogent.ai" in repr(user)


# ── Organization model ───────────────────────────────────────────────


class TestOrganizationModel:
    async def test_create_organization(self, db_session):
        org = await create_organization(db_session, name="Acme Corp", slug="acme-corp")
        assert org.id is not None
        assert org.name == "Acme Corp"
        assert org.slug == "acme-corp"
        assert org.pricing_tier == "explorer"
        assert org.max_users == 10

    async def test_org_unique_slug(self, db_session):
        slug = f"unique-slug-{uuid4().hex[:8]}"
        await create_organization(db_session, slug=slug)
        with pytest.raises(Exception):
            async with db_session.begin_nested():
                await create_organization(db_session, slug=slug)

    async def test_org_default_credits(self, db_session):
        org = await create_organization(db_session, credits_allocated=500)
        assert org.credits_allocated_monthly == 500
        assert org.credits_consumed == 0

    async def test_org_repr(self, db_session):
        org = await create_organization(db_session, slug="repr-org")
        assert "repr-org" in repr(org)


# ── OrgUser (membership) ────────────────────────────────────────────


class TestOrgUserModel:
    async def test_create_membership(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        ou = await create_org_user(db_session, org=org, user=user, role="admin")
        assert ou.org_id == org.id
        assert ou.user_id == user.id
        assert ou.role == "admin"
        assert ou.status == "active"

    async def test_unique_org_user_pair(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        await create_org_user(db_session, org=org, user=user)
        with pytest.raises(Exception):
            async with db_session.begin_nested():
                await create_org_user(db_session, org=org, user=user)

    async def test_org_user_repr(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        ou = await create_org_user(db_session, org=org, user=user)
        assert "OrgUser" in repr(ou)


# ── Subscription model ──────────────────────────────────────────────


class TestSubscriptionModel:
    async def test_create_subscription(self, db_session):
        org = await create_organization(db_session)
        sub = await create_subscription(db_session, org=org, plan_tier="pro")
        assert sub.plan_tier == "pro"
        assert sub.status == "active"
        assert sub.org_id == org.id

    async def test_subscription_defaults(self, db_session):
        org = await create_organization(db_session)
        sub = await create_subscription(db_session, org=org)
        assert sub.currency == "USD"

    async def test_subscription_repr(self, db_session):
        org = await create_organization(db_session)
        sub = await create_subscription(db_session, org=org, plan_tier="enterprise")
        assert "enterprise" in repr(sub)


# ── Industry model ───────────────────────────────────────────────────


class TestIndustryModel:
    async def test_create_industry(self, db_session):
        ind = await create_industry(db_session, name="Energy", slug="energy")
        assert ind.name == "Energy"
        assert ind.slug == "energy"

    async def test_industry_unique_slug(self, db_session):
        slug = f"unique-ind-{uuid4().hex[:8]}"
        await create_industry(db_session, slug=slug)
        with pytest.raises(Exception):
            async with db_session.begin_nested():
                await create_industry(db_session, slug=slug)


# ── Entity model ─────────────────────────────────────────────────────


class TestEntityModel:
    async def test_create_entity(self, db_session):
        ind = await create_industry(db_session)
        ent = await create_entity(
            db_session, name="PayPal", entity_type="company", industry=ind
        )
        assert ent.name == "PayPal"
        assert ent.entity_type == "company"
        assert ent.industry_id == ind.id
        assert ent.verified is False

    async def test_entity_without_industry(self, db_session):
        ent = await create_entity(db_session, name="Orphan Entity")
        assert ent.industry_id is None


# ── SignalContract model ─────────────────────────────────────────────


class TestSignalContractModel:
    async def test_create_signal_contract(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind, source_type="api")
        assert sc.industry_id == ind.id
        assert sc.source_type == "api"
        assert sc.is_active is True
        assert sc.status == "active"
        assert sc.failure_count == 0

    async def test_signal_contract_repr(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind, name="My Contract")
        assert "My Contract" in repr(sc)


# ── Signal model ─────────────────────────────────────────────────────


class TestSignalModel:
    async def test_create_signal(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(
            db_session, contract=sc, confidence=0.92, signal_type="regulatory"
        )
        assert sig.contract_id == sc.id
        assert sig.confidence == 0.92
        assert sig.signal_type == "regulatory"
        assert sig.fetched_at is not None

    async def test_global_signal_null_org(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(db_session, contract=sc)
        assert sig.org_id is None

    async def test_org_scoped_signal(self, db_session):
        ind = await create_industry(db_session)
        org = await create_organization(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(db_session, contract=sc, org=org)
        assert sig.org_id == org.id


# ── SignalEntity (join table) ────────────────────────────────────────


class TestSignalEntityModel:
    async def test_create_signal_entity_link(self, db_session):
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(db_session, contract=sc)
        ent = await create_entity(db_session, industry=ind)
        se = SignalEntity(
            id=uuid4(), signal_id=sig.id, entity_id=ent.id, relevance_score=0.85
        )
        db_session.add(se)
        await db_session.flush()
        assert se.relevance_score == 0.85


# ── IntelligenceBrief model ─────────────────────────────────────────


class TestIntelligenceBriefModel:
    async def test_create_brief(self, db_session):
        ind = await create_industry(db_session)
        brief = await create_intelligence_brief(
            db_session, industry=ind, title="Market Outlook"
        )
        assert brief.title == "Market Outlook"
        assert brief.status == "published"
        assert brief.brief_type == "pre_built"

    async def test_global_brief_null_org(self, db_session):
        ind = await create_industry(db_session)
        brief = await create_intelligence_brief(db_session, industry=ind)
        assert brief.org_id is None


# ── ChatSession & ChatMessage ────────────────────────────────────────


class TestChatModels:
    async def test_create_chat_session(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        cs = await create_chat_session(db_session, user=user, org=org, title="My Chat")
        assert cs.title == "My Chat"
        assert cs.status == "active"

    async def test_create_chat_message(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        cs = await create_chat_session(db_session, user=user, org=org)
        msg = await create_chat_message(
            db_session, session=cs, role="user", content="Hi there"
        )
        assert msg.role == "user"
        assert msg.content == "Hi there"
        assert msg.session_id == cs.id

    async def test_chat_message_roles(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        cs = await create_chat_session(db_session, user=user, org=org)
        for role in ("user", "assistant", "system"):
            msg = await create_chat_message(
                db_session, session=cs, role=role, content=f"{role} msg"
            )
            assert msg.role == role


# ── Document model ───────────────────────────────────────────────────


class TestDocumentModel:
    async def test_create_document(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        doc = await create_document(
            db_session, org=org, user=user, filename="data.csv", size_bytes=2048
        )
        assert doc.filename == "data.csv"
        assert doc.size_bytes == 2048
        assert doc.processing_status == "pending"
        assert doc.visibility == "private"

    async def test_document_soft_delete(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        doc = await create_document(db_session, org=org, user=user)
        assert doc.is_deleted is False
        doc.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()
        assert doc.is_deleted is True


# ── CreditTransaction model ─────────────────────────────────────────


class TestCreditTransactionModel:
    async def test_create_transaction(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        tx = await create_credit_transaction(
            db_session,
            org=org,
            user=user,
            action_type="deep_historical_query",
            credits_consumed=200,
            credits_remaining=800,
        )
        assert tx.action_type == "deep_historical_query"
        assert tx.credits_consumed == 200
        assert tx.credits_remaining == 800

    async def test_transaction_without_user(self, db_session):
        org = await create_organization(db_session)
        tx = await create_credit_transaction(db_session, org=org)
        assert tx.user_id is None


# ── FeatureGate model ────────────────────────────────────────────────


class TestFeatureGateModel:
    async def test_create_feature_gate(self, db_session):
        fg = await create_feature_gate(
            db_session, feature_key="compliance_modules", required_tier="enterprise"
        )
        assert fg.feature_key == "compliance_modules"
        assert fg.required_tier == "enterprise"
        assert fg.is_enterprise_only is False

    async def test_feature_gate_unique_key(self, db_session):
        key = f"feat-{uuid4().hex[:8]}"
        await create_feature_gate(db_session, feature_key=key)
        with pytest.raises(Exception):
            async with db_session.begin_nested():
                await create_feature_gate(db_session, feature_key=key)


# ── Recommendation model ────────────────────────────────────────────


class TestRecommendationModel:
    async def test_create_recommendation(self, db_session):
        rec = Recommendation(
            id=uuid4(),
            source_type="signal",
            source_id=uuid4(),
            target_type="brief",
            target_id=uuid4(),
            score=0.75,
            reason="Related topic",
        )
        db_session.add(rec)
        await db_session.flush()
        await db_session.refresh(rec)
        assert rec.score == 0.75
        assert rec.source_type == "signal"


# ── SearchQuery model ────────────────────────────────────────────────


class TestSearchQueryModel:
    async def test_create_search_query(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)
        sq = SearchQuery(
            id=uuid4(),
            user_id=user.id,
            org_id=org.id,
            query_text="fintech regulation 2026",
            source_count=12,
            response_time_ms=320,
        )
        db_session.add(sq)
        await db_session.flush()
        await db_session.refresh(sq)
        assert sq.query_text == "fintech regulation 2026"
        assert sq.source_count == 12
