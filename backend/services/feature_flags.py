"""
Feature Flag Service

Provides feature gating capabilities for controlled rollouts and plan-based access.

Stage 1 (MVP): Boolean flags with static config
- Simple true/false feature checks
- YAML-based configuration
- Structured logging for all flag checks
- Foundation for future plan-based and user-based overrides

Future stages will add:
- Plan-based rules (free/pro/enterprise)
- User-based overrides (beta testers)
- Org-based overrides (enterprise contracts)
- External storage (DB/Redis)
"""

import logging
from pathlib import Path
from typing import Dict, Any, Literal

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FeatureDefinition(BaseModel):
    """Definition of a single feature flag"""

    enabled: bool = Field(..., description="Whether feature is enabled globally")
    description: str = Field(
        ..., description="Human-readable description of the feature"
    )

    # Stage 2+: Plan-based access (prepared but not enforced yet)
    required_plan: Literal["free", "pro", "enterprise"] | None = Field(
        None, description="Minimum plan required (None = available to all)"
    )

    # Stage 3+: User/Org overrides (prepared but not enforced yet)
    enabled_for_users: list[str] = Field(
        default_factory=list,
        description="User IDs with access even if globally disabled",
    )
    enabled_for_orgs: list[str] = Field(
        default_factory=list,
        description="Org IDs with access even if globally disabled",
    )


class FeatureFlagService:
    """
    Service for evaluating feature flags.

    Stage 1 (MVP): Simple boolean checks from YAML config.
    Future: Plan-based, user-based, and org-based overrides.
    """

    def __init__(self, config_path: Path | None = None):
        """
        Initialize feature flag service.

        Args:
            config_path: Path to features.yaml (defaults to backend/config/features.yaml)
        """
        if config_path is None:
            # Default to backend/config/features.yaml
            backend_dir = Path(__file__).parent.parent
            config_path = backend_dir / "config" / "features.yaml"

        self.config_path = config_path
        self.features: Dict[str, FeatureDefinition] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load feature flags from YAML config file"""
        try:
            if not self.config_path.exists():
                logger.warning(
                    f"Feature flag config not found: {self.config_path}. Using empty config."
                )
                self.features = {}
                return

            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f)

            if not data or "features" not in data:
                logger.warning("No features defined in config. Using empty config.")
                self.features = {}
                return

            # Parse feature definitions
            for feature_name, feature_data in data["features"].items():
                try:
                    self.features[feature_name] = FeatureDefinition(**feature_data)
                except Exception as e:
                    logger.error(
                        f"Failed to parse feature '{feature_name}': {e}", exc_info=True
                    )

            logger.info(
                f"Loaded {len(self.features)} feature flags from {self.config_path}"
            )

        except Exception as e:
            logger.error(f"Failed to load feature flag config: {e}", exc_info=True)
            self.features = {}

    def reload_config(self) -> None:
        """Reload feature flags from config file (for hot-reloading in dev)"""
        logger.info("Reloading feature flag config")
        self._load_config()

    def is_enabled(
        self,
        feature_name: str,
        *,
        user_id: str | None = None,
        org_id: str | None = None,
        plan: Literal["free", "pro", "enterprise"] = "free",
    ) -> bool:
        """
        Check if a feature is enabled.

        Stage 1 (MVP): Only checks global enabled flag.
        Stage 2+: Will also check plan requirements.
        Stage 3+: Will check user/org overrides.

        Args:
            feature_name: Name of the feature to check
            user_id: User ID (for future user-based overrides)
            org_id: Organization ID (for future org-based overrides)
            plan: User's subscription plan (for future plan-based checks)

        Returns:
            True if feature is enabled for this context, False otherwise
        """
        # Feature doesn't exist = disabled
        if feature_name not in self.features:
            logger.warning(
                f"Feature flag '{feature_name}' not defined. Defaulting to disabled.",
                extra={
                    "feature": feature_name,
                    "user_id": user_id,
                    "org_id": org_id,
                    "plan": plan,
                },
            )
            return False

        feature = self.features[feature_name]

        # Stage 3+: Org-level override (highest priority)
        if org_id and org_id in feature.enabled_for_orgs:
            logger.info(
                f"Feature '{feature_name}' enabled via org override",
                extra={
                    "feature": feature_name,
                    "org_id": org_id,
                    "override_type": "org",
                },
            )
            return True

        # Stage 3+: User-level override
        if user_id and user_id in feature.enabled_for_users:
            logger.info(
                f"Feature '{feature_name}' enabled via user override",
                extra={
                    "feature": feature_name,
                    "user_id": user_id,
                    "override_type": "user",
                },
            )
            return True

        # Stage 2+: Plan-based check (prepared but logged only for now)
        if feature.required_plan:
            plan_hierarchy = {"free": 0, "pro": 1, "enterprise": 2}
            has_required_plan = plan_hierarchy.get(plan, 0) >= plan_hierarchy.get(
                feature.required_plan, 0
            )

            if not has_required_plan:
                logger.debug(
                    f"Feature '{feature_name}' requires {feature.required_plan}, user has {plan}",
                    extra={
                        "feature": feature_name,
                        "required_plan": feature.required_plan,
                        "user_plan": plan,
                    },
                )
                # Stage 1: Log but don't enforce (no billing yet)
                # Stage 2: Will return False here

        # Stage 1 (MVP): Global enabled flag
        result = feature.enabled

        logger.debug(
            f"Feature flag check: '{feature_name}' = {result}",
            extra={
                "feature": feature_name,
                "enabled": result,
                "user_id": user_id,
                "org_id": org_id,
                "plan": plan,
            },
        )

        return result

    def get_feature(self, feature_name: str) -> FeatureDefinition | None:
        """Get feature definition by name"""
        return self.features.get(feature_name)

    def list_features(self) -> Dict[str, FeatureDefinition]:
        """Get all feature definitions"""
        return self.features.copy()

    def get_enabled_features(
        self,
        *,
        user_id: str | None = None,
        org_id: str | None = None,
        plan: Literal["free", "pro", "enterprise"] = "free",
    ) -> list[str]:
        """
        Get list of all enabled features for a given context.

        Useful for frontend feature detection.
        """
        enabled = []
        for feature_name in self.features.keys():
            if self.is_enabled(feature_name, user_id=user_id, org_id=org_id, plan=plan):
                enabled.append(feature_name)
        return enabled


# Global singleton instance
_feature_flags_service: FeatureFlagService | None = None


def get_feature_flags_service() -> FeatureFlagService:
    """
    Get global feature flags service instance (singleton).

    Returns:
        FeatureFlagService instance
    """
    global _feature_flags_service

    if _feature_flags_service is None:
        _feature_flags_service = FeatureFlagService()

    return _feature_flags_service


def reload_feature_flags() -> None:
    """Reload feature flags from config file (useful for dev/testing)"""
    service = get_feature_flags_service()
    service.reload_config()
