"""
Middleware tests — feature gating, tier checks, credit balance.

Tests the FastAPI dependency-based middleware in backend/middleware/feature_gating.py.
Uses httpx AsyncClient with dependency overrides for auth/DB.
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from tests.conftest import (
    create_feature_gate,
    create_org_user,
    create_organization,
    create_user,
    make_auth_context,
)

pytestmark = pytest.mark.asyncio

# Tier hierarchy (mirrors GatingService.TIER_HIERARCHY)
TIER_HIERARCHY = {"explorer": 1, "growth": 2, "mid_market": 3, "enterprise": 4}


# =====================================================================
#  get_current_organization
# =====================================================================
class TestGetCurrentOrganization:
    """Tests for the get_current_organization dependency."""

    async def test_returns_org_when_valid(self, app, client, db_session):
        """Returns organization when auth context has valid org_id."""
        from backend.auth.dependencies import get_current_user
        from backend.middleware.feature_gating import get_current_organization

        user = await create_user(db_session)
        org = await create_organization(db_session)
        await create_org_user(db_session, user=user, org=org)

        auth = make_auth_context(user_id=user.id, org_id=org.id)
        app.dependency_overrides[get_current_user] = lambda: auth

        result = await get_current_organization(auth=auth, db=db_session)
        assert result.id == org.id

        app.dependency_overrides.pop(get_current_user, None)

    async def test_raises_400_when_no_org_id(self, app, client, db_session):
        """Raises 400 when auth context has no org_id."""
        from fastapi import HTTPException

        from backend.middleware.feature_gating import get_current_organization

        auth = make_auth_context()
        auth.org_id = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_organization(auth=auth, db=db_session)
        assert exc_info.value.status_code == 400
        assert "No organization context" in str(exc_info.value.detail)

    async def test_raises_404_when_org_not_found(self, app, client, db_session):
        """Raises 404 when org_id does not exist in DB."""
        from fastapi import HTTPException

        from backend.middleware.feature_gating import get_current_organization

        auth = make_auth_context(org_id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await get_current_organization(auth=auth, db=db_session)
        assert exc_info.value.status_code == 404
        assert "Organization not found" in str(exc_info.value.detail)


# =====================================================================
#  require_feature
# =====================================================================
class TestRequireFeature:
    """Tests for the require_feature dependency factory."""

    async def test_no_gate_returns_server_error(self, app, client, db_session):
        """When no FeatureGate exists for the key, access fails closed."""
        from backend.auth.dependencies import get_current_user
        from backend.middleware.feature_gating import require_feature

        user = await create_user(db_session)
        org = await create_organization(db_session, pricing_tier="explorer")
        await create_org_user(db_session, user=user, org=org)

        auth = make_auth_context(user_id=user.id, org_id=org.id)
        app.dependency_overrides[get_current_user] = lambda: auth

        checker = require_feature("nonexistent_feature")
        with pytest.raises(HTTPException) as exc:
            await checker(
                auth=auth,
                organization=org,
                db=db_session,
            )

        assert exc.value.status_code == 500
        assert exc.value.detail["error"] == "feature_gate_misconfigured"

        app.dependency_overrides.pop(get_current_user, None)

    async def test_tier_met_allows_access(self, app, client, db_session):
        """Access granted when org tier meets the gate requirement."""
        from backend.auth.dependencies import get_current_user
        from backend.middleware.feature_gating import require_feature

        user = await create_user(db_session)
        org = await create_organization(db_session, pricing_tier="growth")
        await create_org_user(db_session, user=user, org=org)
        await create_feature_gate(
            db_session, feature_key="premium_reports", required_tier="growth"
        )

        auth = make_auth_context(user_id=user.id, org_id=org.id)
        app.dependency_overrides[get_current_user] = lambda: auth

        checker = require_feature("premium_reports")
        result = await checker(
            auth=auth,
            organization=org,
            db=db_session,
        )
        assert result is True

        app.dependency_overrides.pop(get_current_user, None)

    async def test_tier_not_met_raises_403(self, app, client, db_session):
        """Raises 403 when org tier is below gate requirement."""
        from fastapi import HTTPException

        from backend.auth.dependencies import get_current_user
        from backend.middleware.feature_gating import require_feature

        user = await create_user(db_session)
        org = await create_organization(db_session, pricing_tier="explorer")
        await create_org_user(db_session, user=user, org=org)
        await create_feature_gate(
            db_session, feature_key="enterprise_api", required_tier="enterprise"
        )

        auth = make_auth_context(user_id=user.id, org_id=org.id)
        app.dependency_overrides[get_current_user] = lambda: auth

        checker = require_feature("enterprise_api")
        with pytest.raises(HTTPException) as exc_info:
            await checker(
                auth=auth,
                organization=org,
                db=db_session,
            )
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert detail["error"] == "feature_access_denied"
        assert detail["required_tier"] == "enterprise"
        assert detail["current_tier"] == "explorer"
        assert detail["upgrade_needed"] is True

        app.dependency_overrides.pop(get_current_user, None)

    async def test_role_not_met_raises_403(self, app, client, db_session):
        """Raises 403 when user role is below gate requirement."""
        from fastapi import HTTPException

        from backend.auth.dependencies import get_current_user
        from backend.middleware.feature_gating import require_feature

        user = await create_user(db_session)
        org = await create_organization(db_session, pricing_tier="enterprise")
        await create_org_user(db_session, user=user, org=org)
        await create_feature_gate(
            db_session,
            feature_key="admin_settings",
            required_tier="explorer",
            required_role="admin",
        )

        auth = make_auth_context(user_id=user.id, org_id=org.id, role="viewer")
        app.dependency_overrides[get_current_user] = lambda: auth

        checker = require_feature("admin_settings")
        with pytest.raises(HTTPException) as exc_info:
            await checker(
                auth=auth,
                organization=org,
                db=db_session,
            )
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert detail["error"] == "role_access_denied"
        assert detail["required_role"] == "admin"

        app.dependency_overrides.pop(get_current_user, None)


# =====================================================================
#  require_tier
# =====================================================================
class TestRequireTier:
    """Tests for the require_tier dependency factory."""

    async def test_tier_met(self, app, client, db_session):
        """Returns organization when tier requirement is met."""
        from backend.middleware.feature_gating import require_tier

        org = await create_organization(db_session, pricing_tier="enterprise")

        checker = require_tier("enterprise")
        result = await checker(organization=org, db=db_session)
        assert result.id == org.id

    async def test_tier_exceeds_requirement(self, app, client, db_session):
        """Returns organization when tier exceeds requirement."""
        from backend.middleware.feature_gating import require_tier

        org = await create_organization(db_session, pricing_tier="enterprise")

        checker = require_tier("growth")
        result = await checker(organization=org, db=db_session)
        assert result.id == org.id

    async def test_tier_below_raises_403(self, app, client, db_session):
        """Raises 403 when org tier is below requirement."""
        from fastapi import HTTPException

        from backend.middleware.feature_gating import require_tier

        org = await create_organization(db_session, pricing_tier="explorer")

        checker = require_tier("enterprise")
        with pytest.raises(HTTPException) as exc_info:
            await checker(organization=org, db=db_session)
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert detail["error"] == "tier_access_denied"
        assert detail["current_tier"] == "explorer"
        assert detail["required_tier"] == "enterprise"


# =====================================================================
#  check_credit_balance
# =====================================================================
class TestCheckCreditBalance:
    """Tests for the check_credit_balance dependency."""

    async def test_returns_org_with_sufficient_credits(self, app, client, db_session):
        """Returns organization when credits are sufficient."""
        from backend.middleware.feature_gating import check_credit_balance

        org = await create_organization(
            db_session, credits_allocated=1000, credits_consumed=100
        )

        result = await check_credit_balance(organization=org, db=db_session)
        assert result.id == org.id

    async def test_returns_org_with_low_credits(self, app, client, db_session):
        """Returns organization even with low credits (no blocking)."""
        from backend.middleware.feature_gating import check_credit_balance

        org = await create_organization(
            db_session, credits_allocated=100, credits_consumed=95
        )

        result = await check_credit_balance(organization=org, db=db_session)
        assert result.id == org.id
