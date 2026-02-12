"""
Services module

Business logic and domain services.
"""

from backend.services.feature_flags import FeatureFlagService, get_feature_flags_service
from backend.services.signal_acquisition import SignalAcquisitionService

__all__ = [
    "FeatureFlagService",
    "get_feature_flags_service",
    "SignalAcquisitionService",
    # Sprint 4 — lazy-imported via backend.services.{module}
    # DeepSearchService → backend.services.deep_search
    # RecommendationService → backend.services.recommendation
]
