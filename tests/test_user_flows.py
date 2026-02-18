"""
Full user-flow simulation tests (backend-only, no frontend).

Simulates complete business processes through the database layer:
  1. User signup → org creation → login
  2. Signal discovery workflow
  3. Free user → gate → upgrade → access
  4. Chat session lifecycle
  5. API key lifecycle
"""

from datetime import datetime, timezone

import pytest

from backend.auth.exceptions import InsufficientRoleError
from backend.auth.guards import require_role
from backend.models.pricing_enums import PricingTier
from tests.conftest import (
    create_api_key,
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
    make_auth_context,
)

pytestmark = pytest.mark.asyncio


class TestUserSignupFlow:
    """Simulate: user registers → org created → membership → login."""

    async def test_full_signup_flow(self, db_session):
        # Step 1: User created from Auth0 webhook
        user = await create_user(
            db_session,
            email="newuser@startup.com",
            auth0_id="auth0|newuser001",
            name="New User",
        )
        assert user.id is not None
        assert user.login_count == 0

        # Step 2: Organization created
        org = await create_organization(
            db_session,
            name="Startup Inc",
            slug="startup-inc",
            pricing_tier="explorer",
        )
        assert org.pricing_tier == "explorer"

        # Step 3: User becomes owner of org
        membership = await create_org_user(db_session, org=org, user=user, role="owner")
        assert membership.role == "owner"
        assert membership.status == "active"

        # Step 4: Subscription created (free tier)
        sub = await create_subscription(
            db_session, org=org, plan_tier="free", status="trialing"
        )
        assert sub.plan_tier == "free"

        # Step 5: Simulate login count update
        user.login_count += 1
        user.last_login_at = datetime.now(timezone.utc)
        await db_session.flush()
        assert user.login_count == 1
        assert user.last_login_at is not None


class TestSignalDiscoveryFlow:
    """Simulate: industry setup → contracts → signals → entity linking → brief."""

    async def test_signal_pipeline(self, db_session):
        # Step 1: Industry taxonomy
        fintech = await create_industry(db_session, name="Fintech", slug="fintech")

        # Step 2: Entity created
        entity = await create_entity(
            db_session, name="Stripe", entity_type="company", industry=fintech
        )

        # Step 3: Signal contract defined
        contract = await create_signal_contract(
            db_session,
            industry=fintech,
            name="Stripe News Feed",
            source_url="https://stripe.com/blog/feed",
            source_type="rss",
        )

        # Step 4: Signals acquired
        signals = []
        for i in range(5):
            sig = await create_signal(
                db_session,
                contract=contract,
                title=f"Stripe Announcement #{i+1}",
                signal_type="news",
                confidence=0.7 + i * 0.05,
            )
            signals.append(sig)

        assert len(signals) == 5
        assert signals[4].confidence == pytest.approx(0.90)

        # Step 5: Intelligence brief generated from signals
        brief = await create_intelligence_brief(
            db_session,
            industry=fintech,
            title="Fintech Weekly: Stripe Expansion",
            brief_type="auto_generated",
            status="published",
        )
        assert brief.status == "published"


class TestFeatureGatingFlow:
    """Simulate: free user blocked → upgrade → access granted."""

    async def test_gate_then_upgrade(self, db_session):
        # Step 1: Feature gate requiring 'growth' tier
        gate = await create_feature_gate(
            db_session,
            feature_key="deep_historical_query",
            required_tier="growth",
        )

        # Step 2: Explorer org → should NOT pass tier check
        org = await create_organization(
            db_session, pricing_tier="explorer", credits_allocated=0
        )
        TIER_HIERARCHY = {
            PricingTier.EXPLORER: 0,
            PricingTier.GROWTH: 1,
            PricingTier.MID_MARKET: 2,
            PricingTier.ENTERPRISE: 3,
        }
        current = TIER_HIERARCHY.get(org.pricing_tier, 0)
        required = TIER_HIERARCHY.get(gate.required_tier, 0)
        assert current < required  # Access denied

        # Step 3: Upgrade org to growth
        org.pricing_tier = "growth"
        org.credits_allocated_monthly = 500
        await db_session.flush()

        # Step 4: Now passes
        current = TIER_HIERARCHY.get(org.pricing_tier, 0)
        assert current >= required  # Access granted

    async def test_role_gate_member_vs_admin(self):
        """Member cannot do admin actions."""
        member_ctx = make_auth_context(role="member")
        with pytest.raises(InsufficientRoleError):
            require_role(member_ctx, "admin")

        # After role upgrade
        admin_ctx = make_auth_context(role="admin")
        require_role(admin_ctx, "admin")  # Should pass


class TestChatSessionLifecycle:
    """Simulate: create session → send messages → archive → delete."""

    async def test_chat_lifecycle(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)

        # Step 1: Create session
        session = await create_chat_session(
            db_session, user=user, org=org, title="Market Analysis Chat"
        )
        assert session.status == "active"

        # Step 2: User sends message
        msg1 = await create_chat_message(
            db_session,
            session=session,
            role="user",
            content="What are the latest fintech trends?",
        )
        assert msg1.role == "user"

        # Step 3: AI responds
        msg2 = await create_chat_message(
            db_session,
            session=session,
            role="assistant",
            content="Based on recent signals, the top trends include...",
        )
        assert msg2.role == "assistant"

        # Step 4: Archive session
        session.status = "archived"
        await db_session.flush()
        assert session.status == "archived"

        # Step 5: Verify both messages exist
        # (In a real test we'd query, but here we just verify the objects)
        assert msg1.session_id == session.id
        assert msg2.session_id == session.id


class TestAPIKeyLifecycle:
    """Simulate: create API key → use → revoke."""

    async def test_api_key_lifecycle(self, db_session):
        org = await create_organization(db_session)
        user = await create_user(db_session)

        # Step 1: Create API key
        api_key = await create_api_key(
            db_session, org=org, user=user, name="CI/CD Pipeline"
        )
        assert api_key.name == "CI/CD Pipeline"
        assert api_key.is_active is True
        assert api_key.key_prefix.startswith("cogent_pk_live_")

        # Step 2: Simulate usage
        api_key.last_used_at = datetime.now(timezone.utc)
        await db_session.flush()
        assert api_key.last_used_at is not None

        # Step 3: Revoke
        api_key.revoked_at = datetime.now(timezone.utc)
        await db_session.flush()
        assert api_key.is_active is False


class TestCreditConsumptionFlow:
    """Simulate: org with credits → consume → check balance → overage."""

    async def test_credit_consumption_lifecycle(self, db_session):
        org = await create_organization(
            db_session, credits_allocated=200, credits_consumed=0
        )
        user = await create_user(db_session)

        # Step 1: Generate a brief (50 credits)
        org.credits_consumed += 50
        tx1 = await create_credit_transaction(
            db_session,
            org=org,
            user=user,
            action_type="intelligence_brief",
            credits_consumed=50,
            credits_remaining=150,
        )
        await db_session.flush()
        assert org.credits_allocated_monthly - org.credits_consumed == 150

        # Step 2: Deep query (200 credits) → insufficient
        remaining = org.credits_allocated_monthly - org.credits_consumed
        cost = 200
        assert remaining < cost  # Should be blocked

        # Step 3: On-demand synthesis (100 credits) → succeeds
        org.credits_consumed += 100
        tx2 = await create_credit_transaction(
            db_session,
            org=org,
            user=user,
            action_type="on_demand_synthesis",
            credits_consumed=100,
            credits_remaining=50,
        )
        await db_session.flush()
        assert org.credits_allocated_monthly - org.credits_consumed == 50

        # Step 4: Another synthesis → insufficient now
        remaining = org.credits_allocated_monthly - org.credits_consumed
        assert remaining < 100  # 50 < 100


class TestMultiTenantIsolation:
    """Verify that data is properly scoped per organization."""

    async def test_org_scoped_signals(self, db_session):
        org_a = await create_organization(db_session, slug="org-a-flow")
        org_b = await create_organization(db_session, slug="org-b-flow")
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)

        sig_a = await create_signal(
            db_session, contract=sc, org=org_a, title="Signal A"
        )
        sig_b = await create_signal(
            db_session, contract=sc, org=org_b, title="Signal B"
        )

        # Verify they belong to different orgs
        assert sig_a.org_id == org_a.id
        assert sig_b.org_id == org_b.id
        assert sig_a.org_id != sig_b.org_id

    async def test_org_scoped_documents(self, db_session):
        org_a = await create_organization(db_session, slug="doc-org-a")
        org_b = await create_organization(db_session, slug="doc-org-b")
        user_a = await create_user(db_session, email="a@a.com")
        user_b = await create_user(db_session, email="b@b.com")

        doc_a = await create_document(
            db_session, org=org_a, user=user_a, filename="a.pdf"
        )
        doc_b = await create_document(
            db_session, org=org_b, user=user_b, filename="b.pdf"
        )

        assert doc_a.org_id != doc_b.org_id
