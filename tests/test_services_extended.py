"""
Extended service layer tests covering:
- CreditService: credit consumption, balance, overage
- GatingService: tier/role-based feature access
- PricingService: subscription pricing, overage
- TrialService: trial lifecycle (start, expiry, conversion)
- FeatureFlagService: YAML-based feature flags

All services tested against the real async SQLite DB (no mocks).
"""

import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.feature_gate import FeatureGate
from backend.models.pricing_config import PricingConfig
from backend.models.pricing_enums import PricingTier, TrialStatus
from backend.services.credit_service import CreditService
from backend.services.feature_flags import FeatureFlagService
from backend.services.gating_service import GatingService
from backend.services.pricing_service import PricingService
from backend.services.trial_service import TrialService

# Helpers imported from conftest
from tests.conftest import create_organization, create_user


# ---------------------------------------------------------------------------
# Helper: create a PricingConfig row
# ---------------------------------------------------------------------------
async def create_pricing_config(
    db: AsyncSession,
    config_key: str,
    config_value,
    user_id=None,
) -> PricingConfig:
    pc = PricingConfig(
        config_key=config_key,
        config_value=config_value,
        updated_by=user_id,
    )
    db.add(pc)
    await db.flush()
    await db.refresh(pc)
    return pc


# =====================================================================
#  CreditService Tests
# =====================================================================
class TestCreditService:
    """Tests for CreditService credit consumption and balance."""

    async def test_consume_credits_atomic_success(self, db_session: AsyncSession):
        """Consume credits atomically when balance is sufficient."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, credits_allocated=1000, credits_consumed=0
        )
        svc = CreditService(db_session)

        txn = await svc.consume_credits_atomic(
            org_id=org.id,
            user_id=user.id,
            action_type="intelligence_brief",
        )
        assert txn is not None
        assert txn.credits_consumed == 50  # default for intelligence_brief
        assert txn.credits_remaining == 950

    async def test_consume_credits_atomic_insufficient(self, db_session: AsyncSession):
        """Returns None when credits are insufficient."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, credits_allocated=10, credits_consumed=0
        )
        svc = CreditService(db_session)

        result = await svc.consume_credits_atomic(
            org_id=org.id,
            user_id=user.id,
            action_type="intelligence_brief",  # costs 50
        )
        assert result is None

    async def test_consume_credits_atomic_free_action(self, db_session: AsyncSession):
        """Free actions (signal_view) still create a transaction with 0 credits."""
        user = await create_user(db_session)
        org = await create_organization(db_session)
        svc = CreditService(db_session)

        txn = await svc.consume_credits_atomic(
            org_id=org.id,
            user_id=user.id,
            action_type="signal_view",
        )
        assert txn is not None
        assert txn.credits_consumed == 0

    async def test_consume_credits_atomic_org_not_found(self, db_session: AsyncSession):
        """Raises ValueError for unknown org_id."""
        svc = CreditService(db_session)

        with pytest.raises(ValueError, match="Organization not found"):
            await svc.consume_credits_atomic(
                org_id=uuid4(),
                user_id=uuid4(),
                action_type="intelligence_brief",
            )

    async def test_consume_credits_atomic_custom_amount(self, db_session: AsyncSession):
        """Custom credit amount overrides default."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, credits_allocated=500, credits_consumed=0
        )
        svc = CreditService(db_session)

        txn = await svc.consume_credits_atomic(
            org_id=org.id,
            user_id=user.id,
            action_type="intelligence_brief",
            credits=30,
        )
        assert txn is not None
        assert txn.credits_consumed == 30
        assert txn.credits_remaining == 470

    async def test_get_credit_balance(self, db_session: AsyncSession):
        """Get credit balance summary for an organization."""
        org = await create_organization(
            db_session, credits_allocated=1000, credits_consumed=200
        )
        svc = CreditService(db_session)

        balance = await svc.get_credit_balance(org.id)
        assert balance["allocated"] == 1000
        assert balance["consumed"] == 200
        assert balance["remaining"] == 800
        assert balance["overage"] == 0

    async def test_get_credit_balance_with_overage(self, db_session: AsyncSession):
        """Balance with overage returns correct numbers."""
        org = await create_organization(
            db_session, credits_allocated=100, credits_consumed=150
        )
        svc = CreditService(db_session)

        balance = await svc.get_credit_balance(org.id)
        assert balance["allocated"] == 100
        assert balance["consumed"] == 150
        assert balance["remaining"] == 0  # clamped to 0
        assert balance["overage"] == 50

    async def test_get_credit_balance_not_found(self, db_session: AsyncSession):
        """Raises ValueError for unknown org_id."""
        svc = CreditService(db_session)

        with pytest.raises(ValueError, match="Organization not found"):
            await svc.get_credit_balance(uuid4())

    async def test_check_sufficient_credits_true(self, db_session: AsyncSession):
        """Sufficient credits returns True."""
        org = await create_organization(
            db_session, credits_allocated=1000, credits_consumed=0
        )
        svc = CreditService(db_session)

        result = await svc.check_sufficient_credits(org.id, "intelligence_brief")
        assert result is True

    async def test_check_sufficient_credits_false(self, db_session: AsyncSession):
        """Insufficient credits returns False."""
        org = await create_organization(
            db_session, credits_allocated=10, credits_consumed=0
        )
        svc = CreditService(db_session)

        result = await svc.check_sufficient_credits(org.id, "intelligence_brief")
        assert result is False

    async def test_get_action_credit_cost(self, db_session: AsyncSession):
        """Get credit cost for known and unknown actions."""
        svc = CreditService(db_session)

        assert svc.get_action_credit_cost("intelligence_brief") == 50
        assert svc.get_action_credit_cost("on_demand_synthesis") == 100
        assert svc.get_action_credit_cost("signal_view") == 0
        assert svc.get_action_credit_cost("unknown_action") == 0


# =====================================================================
#  GatingService Tests
# =====================================================================
class TestGatingService:
    """Tests for tier/role-based feature access control."""

    async def _make_gate(
        self,
        db: AsyncSession,
        feature_key: str,
        required_tier: str = None,
        required_role: str = None,
    ) -> FeatureGate:
        gate = FeatureGate(
            feature_key=feature_key,
            required_tier=required_tier or "explorer",
            required_role=required_role,
        )
        db.add(gate)
        await db.flush()
        await db.refresh(gate)
        return gate

    async def test_no_gate_allows_access(self, db_session: AsyncSession):
        """Features without a gate are accessible by all."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, pricing_tier=PricingTier.EXPLORER.value
        )
        svc = GatingService(db_session)

        result = await svc.check_feature_access(org, user, "nonexistent_feature")
        assert result is True

    async def test_tier_meets_requirement(self, db_session: AsyncSession):
        """Access granted when org tier meets requirement."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, pricing_tier=PricingTier.GROWTH.value
        )
        await self._make_gate(
            db_session,
            "premium_feature",
            required_tier=PricingTier.GROWTH.value,
        )
        svc = GatingService(db_session)

        result = await svc.check_feature_access(org, user, "premium_feature")
        assert result is True

    async def test_tier_below_requirement(self, db_session: AsyncSession):
        """Access denied when org tier is below requirement."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, pricing_tier=PricingTier.EXPLORER.value
        )
        await self._make_gate(
            db_session,
            "premium_feature",
            required_tier=PricingTier.ENTERPRISE.value,
        )
        svc = GatingService(db_session)

        result = await svc.check_feature_access(org, user, "premium_feature")
        assert result is False

    async def test_tier_exceeds_requirement(self, db_session: AsyncSession):
        """Access granted when org tier exceeds requirement."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, pricing_tier=PricingTier.ENTERPRISE.value
        )
        await self._make_gate(
            db_session,
            "basic_feature",
            required_tier=PricingTier.GROWTH.value,
        )
        svc = GatingService(db_session)

        result = await svc.check_feature_access(org, user, "basic_feature")
        assert result is True

    async def test_require_feature_raises_on_denied(self, db_session: AsyncSession):
        """require_feature raises PermissionError when access denied."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, pricing_tier=PricingTier.EXPLORER.value
        )
        await self._make_gate(
            db_session,
            "enterprise_only",
            required_tier=PricingTier.ENTERPRISE.value,
        )
        svc = GatingService(db_session)

        with pytest.raises(PermissionError, match="higher tier"):
            await svc.require_feature(org, user, "enterprise_only")

    async def test_get_feature_access_map(self, db_session: AsyncSession):
        """Access map returns correct verdicts for all gates."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, pricing_tier=PricingTier.GROWTH.value
        )
        await self._make_gate(
            db_session,
            "allowed_feature",
            required_tier=PricingTier.EXPLORER.value,
        )
        await self._make_gate(
            db_session,
            "blocked_feature",
            required_tier=PricingTier.ENTERPRISE.value,
        )
        svc = GatingService(db_session)

        access_map = await svc.get_feature_access_map(org, user)
        assert access_map["allowed_feature"] is True
        assert access_map["blocked_feature"] is False

    async def test_get_available_features(self, db_session: AsyncSession):
        """Returns only features available to the org."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, pricing_tier=PricingTier.GROWTH.value
        )
        await self._make_gate(
            db_session, "feat_a", required_tier=PricingTier.EXPLORER.value
        )
        await self._make_gate(
            db_session, "feat_b", required_tier=PricingTier.ENTERPRISE.value
        )
        svc = GatingService(db_session)

        available = await svc.get_available_features(org, user)
        assert "feat_a" in available
        assert "feat_b" not in available

    async def test_get_blocked_features(self, db_session: AsyncSession):
        """Returns only features blocked for the org."""
        user = await create_user(db_session)
        org = await create_organization(
            db_session, pricing_tier=PricingTier.EXPLORER.value
        )
        await self._make_gate(
            db_session, "feat_x", required_tier=PricingTier.GROWTH.value
        )
        svc = GatingService(db_session)

        blocked = await svc.get_blocked_features(org, user)
        assert "feat_x" in blocked

    async def test_check_tier_access_helper(self, db_session: AsyncSession):
        """_check_tier_access correctly compares tier levels."""
        svc = GatingService(db_session)

        assert (
            svc._check_tier_access(PricingTier.ENTERPRISE, PricingTier.EXPLORER) is True
        )
        assert (
            svc._check_tier_access(PricingTier.EXPLORER, PricingTier.ENTERPRISE)
            is False
        )
        assert svc._check_tier_access(PricingTier.GROWTH, PricingTier.GROWTH) is True


# =====================================================================
#  PricingService Tests
# =====================================================================
class TestPricingService:
    """Tests for subscription pricing and overage calculation."""

    async def _seed_tier_price(self, db: AsyncSession, tier: str, price: int):
        """Insert a pricing config for a tier."""
        await create_pricing_config(db, f"standard_price_{tier}", price)

    async def test_calculate_subscription_price_standard(
        self, db_session: AsyncSession
    ):
        """Standard price for non-beta org."""
        await self._seed_tier_price(db_session, "growth", 299)
        org = await create_organization(db_session, pricing_tier="growth")
        svc = PricingService(db_session)

        price = await svc.calculate_subscription_price(org)
        assert price == Decimal("299")

    async def test_calculate_overage_cost_no_overage(self, db_session: AsyncSession):
        """No overage returns 0."""
        org = await create_organization(
            db_session, credits_allocated=1000, credits_consumed=500
        )
        svc = PricingService(db_session)

        cost = await svc.calculate_overage_cost(org)
        assert cost == Decimal("0")

    async def test_calculate_overage_cost_with_overage(self, db_session: AsyncSession):
        """Overage calculated correctly."""
        org = await create_organization(
            db_session, credits_allocated=100, credits_consumed=150
        )
        # overage_rate defaults to 0.10
        svc = PricingService(db_session)

        cost = await svc.calculate_overage_cost(org)
        assert cost == Decimal("5.0")  # 50 * 0.10

    async def test_get_pricing_summary(self, db_session: AsyncSession):
        """Pricing summary contains all expected keys."""
        await self._seed_tier_price(db_session, "explorer", 0)
        org = await create_organization(
            db_session,
            pricing_tier="explorer",
            credits_allocated=500,
            credits_consumed=100,
        )
        svc = PricingService(db_session)

        summary = await svc.get_pricing_summary(org)
        assert summary["tier"] == "explorer"
        assert "subscription_price" in summary
        assert "overage_cost" in summary
        assert "total_monthly_cost" in summary

    async def test_get_tier_upgrade_options(self, db_session: AsyncSession):
        """Returns upgrade options above current tier."""
        for tier, price in [
            ("explorer", 0),
            ("growth", 99),
            ("mid_market", 299),
            ("enterprise", 999),
        ]:
            await self._seed_tier_price(db_session, tier, price)
        svc = PricingService(db_session)

        options = await svc.get_tier_upgrade_options("explorer")
        tier_names = [o["tier"] for o in options]
        assert "growth" in tier_names
        assert "enterprise" in tier_names
        assert "explorer" not in tier_names

    async def test_get_tier_upgrade_options_enterprise(self, db_session: AsyncSession):
        """Enterprise has no upgrade options."""
        svc = PricingService(db_session)

        options = await svc.get_tier_upgrade_options("enterprise")
        assert options == []


# =====================================================================
#  TrialService Tests
# =====================================================================
class TestTrialService:
    """Tests for trial lifecycle management."""

    async def _seed_trial_config(self, db: AsyncSession):
        """Seed default trial config values."""
        await create_pricing_config(db, "trial_duration_days", 30)
        await create_pricing_config(db, "trial_credits", 10000)

    async def test_start_trial(self, db_session: AsyncSession):
        """Start trial sets correct status, tier, and credits."""
        await self._seed_trial_config(db_session)
        org = await create_organization(
            db_session, pricing_tier=PricingTier.EXPLORER.value
        )
        svc = TrialService(db_session)

        result = await svc.start_trial(org)
        assert result.trial_status == TrialStatus.ACTIVE.value
        assert result.pricing_tier == PricingTier.GROWTH.value
        assert result.credits_allocated_monthly == 10000
        assert result.credits_consumed == 0
        assert result.trial_start_date is not None
        assert result.trial_end_date is not None

    async def test_check_trial_expiry_still_active(self, db_session: AsyncSession):
        """Active trial within date range stays active."""
        org = await create_organization(
            db_session, pricing_tier=PricingTier.GROWTH.value
        )
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_end_date = datetime.now(timezone.utc) + timedelta(days=10)
        await db_session.flush()

        svc = TrialService(db_session)
        result = await svc.check_trial_expiry(org)
        assert result.trial_status == TrialStatus.ACTIVE.value

    async def test_check_trial_expiry_expired_no_subscription(
        self, db_session: AsyncSession
    ):
        """Expired trial without subscription downgrades to Explorer."""
        org = await create_organization(
            db_session, pricing_tier=PricingTier.GROWTH.value
        )
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_end_date = datetime.now(timezone.utc) - timedelta(days=1)
        org.billing_cycle_start = None  # no subscription
        await db_session.flush()

        svc = TrialService(db_session)
        result = await svc.check_trial_expiry(org)
        assert result.trial_status == TrialStatus.EXPIRED.value
        assert result.pricing_tier == PricingTier.EXPLORER.value
        assert result.credits_allocated_monthly == 0

    async def test_check_trial_expiry_converted(self, db_session: AsyncSession):
        """Expired trial with active subscription converts."""
        from datetime import date

        org = await create_organization(
            db_session, pricing_tier=PricingTier.GROWTH.value
        )
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_end_date = datetime.now(timezone.utc) - timedelta(days=1)
        org.billing_cycle_start = date.today()  # has subscription
        await db_session.flush()

        svc = TrialService(db_session)
        result = await svc.check_trial_expiry(org)
        assert result.trial_status == TrialStatus.CONVERTED.value

    async def test_check_trial_expiry_not_active(self, db_session: AsyncSession):
        """Non-active trial status is returned unchanged."""
        org = await create_organization(db_session)
        org.trial_status = TrialStatus.EXPIRED.value
        await db_session.flush()

        svc = TrialService(db_session)
        result = await svc.check_trial_expiry(org)
        assert result.trial_status == TrialStatus.EXPIRED.value

    async def test_convert_trial_to_paid(self, db_session: AsyncSession):
        """Convert trial sets correct tier, status, and credits."""
        org = await create_organization(
            db_session, pricing_tier=PricingTier.GROWTH.value
        )
        org.trial_status = TrialStatus.ACTIVE.value
        await db_session.flush()

        svc = TrialService(db_session)
        result = await svc.convert_trial_to_paid(org, PricingTier.MID_MARKET.value)

        assert result.trial_status == TrialStatus.CONVERTED.value
        assert result.pricing_tier == PricingTier.MID_MARKET.value
        assert result.credits_allocated_monthly == 25000
        assert result.billing_cycle_start is not None

    async def test_get_active_trials(self, db_session: AsyncSession):
        """Returns only organizations with active trials."""
        active_org = await create_organization(
            db_session, name="Active Trial Org", slug="active-trial"
        )
        active_org.trial_status = TrialStatus.ACTIVE.value
        expired_org = await create_organization(
            db_session, name="Expired Org", slug="expired-trial"
        )
        expired_org.trial_status = TrialStatus.EXPIRED.value
        await db_session.flush()

        svc = TrialService(db_session)
        actives = await svc.get_active_trials()
        active_ids = [o.id for o in actives]
        assert active_org.id in active_ids
        assert expired_org.id not in active_ids

    async def test_get_expiring_trials(self, db_session: AsyncSession):
        """Returns trials expiring within N days."""
        org_soon = await create_organization(
            db_session, name="Soon Org", slug="soon-trial"
        )
        org_soon.trial_status = TrialStatus.ACTIVE.value
        org_soon.trial_end_date = datetime.now(timezone.utc) + timedelta(days=3)

        org_later = await create_organization(
            db_session, name="Later Org", slug="later-trial"
        )
        org_later.trial_status = TrialStatus.ACTIVE.value
        org_later.trial_end_date = datetime.now(timezone.utc) + timedelta(days=30)
        await db_session.flush()

        svc = TrialService(db_session)
        expiring = await svc.get_expiring_trials(days=7)
        expiring_ids = [o.id for o in expiring]
        assert org_soon.id in expiring_ids
        assert org_later.id not in expiring_ids


# =====================================================================
#  FeatureFlagService Tests (YAML-based, no DB needed)
# =====================================================================
class TestFeatureFlagService:
    """Tests for YAML feature flag evaluation."""

    def _write_yaml(self, content: str) -> Path:
        """Write YAML content to a temp file and return path."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        tmp.write(content)
        tmp.flush()
        tmp.close()
        return Path(tmp.name)

    def test_load_valid_config(self):
        """Loads features from a valid YAML file."""
        path = self._write_yaml(
            """
features:
  my_feature:
    enabled: true
    description: "Test feature"
"""
        )
        svc = FeatureFlagService(config_path=path)
        assert "my_feature" in svc.features
        assert svc.features["my_feature"].enabled is True

    def test_is_enabled_true(self):
        """Enabled feature returns True."""
        path = self._write_yaml(
            """
features:
  active:
    enabled: true
    description: "Active"
"""
        )
        svc = FeatureFlagService(config_path=path)
        assert svc.is_enabled("active") is True

    def test_is_enabled_false(self):
        """Disabled feature returns False."""
        path = self._write_yaml(
            """
features:
  inactive:
    enabled: false
    description: "Inactive"
"""
        )
        svc = FeatureFlagService(config_path=path)
        assert svc.is_enabled("inactive") is False

    def test_undefined_feature_returns_false(self):
        """Undefined feature defaults to disabled."""
        path = self._write_yaml("features: {}")
        svc = FeatureFlagService(config_path=path)
        assert svc.is_enabled("nope") is False

    def test_missing_file_uses_empty_config(self):
        """Missing config file results in empty feature set."""
        svc = FeatureFlagService(config_path=Path("/nonexistent/features.yaml"))
        assert svc.features == {}
        assert svc.is_enabled("anything") is False

    def test_org_override(self):
        """Org-level override enables disabled feature."""
        path = self._write_yaml(
            """
features:
  beta_only:
    enabled: false
    description: "Only for specific orgs"
    enabled_for_orgs:
      - "org-123"
"""
        )
        svc = FeatureFlagService(config_path=path)
        assert svc.is_enabled("beta_only", org_id="org-123") is True
        assert svc.is_enabled("beta_only", org_id="org-456") is False

    def test_user_override(self):
        """User-level override enables disabled feature."""
        path = self._write_yaml(
            """
features:
  alpha:
    enabled: false
    description: "Alpha feature"
    enabled_for_users:
      - "user-abc"
"""
        )
        svc = FeatureFlagService(config_path=path)
        assert svc.is_enabled("alpha", user_id="user-abc") is True
        assert svc.is_enabled("alpha", user_id="user-xyz") is False

    def test_get_feature(self):
        """Get feature definition by name."""
        path = self._write_yaml(
            """
features:
  feat:
    enabled: true
    description: "A feature"
"""
        )
        svc = FeatureFlagService(config_path=path)
        feat = svc.get_feature("feat")
        assert feat is not None
        assert feat.description == "A feature"
        assert svc.get_feature("nonexistent") is None

    def test_list_features(self):
        """List all features."""
        path = self._write_yaml(
            """
features:
  a:
    enabled: true
    description: "A"
  b:
    enabled: false
    description: "B"
"""
        )
        svc = FeatureFlagService(config_path=path)
        features = svc.list_features()
        assert len(features) == 2
        assert "a" in features
        assert "b" in features

    def test_get_enabled_features(self):
        """Returns only enabled feature names."""
        path = self._write_yaml(
            """
features:
  feature_active:
    enabled: true
    description: "Active"
  feature_disabled:
    enabled: false
    description: "Disabled"
"""
        )
        svc = FeatureFlagService(config_path=path)
        enabled = svc.get_enabled_features()
        assert "feature_active" in enabled
        assert "feature_disabled" not in enabled

    def test_reload_config(self):
        """Reload picks up changes."""
        path = self._write_yaml(
            """
features:
  toggle:
    enabled: false
    description: "Togglable"
"""
        )
        svc = FeatureFlagService(config_path=path)
        assert svc.is_enabled("toggle") is False

        # Overwrite
        with open(path, "w") as f:
            f.write(
                """
features:
  toggle:
    enabled: true
    description: "Togglable"
"""
            )

        svc.reload_config()
        assert svc.is_enabled("toggle") is True

    def test_load_real_features_yaml(self):
        """Loads the actual project features.yaml without error."""
        real_path = (
            Path(__file__).parent.parent / "backend" / "config" / "features.yaml"
        )
        if real_path.exists():
            svc = FeatureFlagService(config_path=real_path)
            assert len(svc.features) > 0
