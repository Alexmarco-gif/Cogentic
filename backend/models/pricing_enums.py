"""Enums for pricing and feature gating system"""

from enum import Enum


class PricingTier(str, Enum):
    """Organization pricing tiers"""

    EXPLORER = "explorer"
    GROWTH = "growth"
    MID_MARKET = "mid_market"
    ENTERPRISE = "enterprise"


class TrialStatus(str, Enum):
    """Trial account status"""

    ACTIVE = "active"
    EXPIRED = "expired"
    CONVERTED = "converted"


class UserRole(str, Enum):
    """User roles within an organization"""

    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
