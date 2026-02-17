"""SQLAlchemy ORM Models"""

from backend.models.ai_job import AIJob
from backend.models.ai_usage_log import AIUsageLog
from backend.models.api_key import APIKey
from backend.models.audit_log import AuditLog
from backend.models.base import Base
from backend.models.brief_signal import BriefSignal
from backend.models.causal_event import CausalEdge, CausalEvent
from backend.models.chat_message import ChatMessage
from backend.models.chat_session import ChatSession
from backend.models.document import Document
from backend.models.entity import Entity
from backend.models.entity_alias import EntityAlias
from backend.models.entity_relationship import EntityRelationship
from backend.models.entity_source_profile import EntitySourceProfile
from backend.models.industry import Industry
from backend.models.intelligence_brief import IntelligenceBrief
from backend.models.ml_model_registry import MLModelRegistry
from backend.models.ml_model_run import MLModelRun
from backend.models.moat_metric import MoatMetricSnapshot
from backend.models.org_user import OrgUser
from backend.models.organization import Organization
from backend.models.recommendation import Recommendation
from backend.models.regulatory_knowledge import (
    RegulatoryEvent,
    RegulatoryImpact,
    RegulatoryPattern,
    RegulatoryRule,
)
from backend.models.beta_account import BetaAccount
from backend.models.credit_transaction import CreditTransaction
from backend.models.feature_gate import FeatureGate
from backend.models.pricing_config import PricingConfig
from backend.models.search_query import SearchQuery
from backend.models.signal import Signal
from backend.models.signal_contract import SignalContract
from backend.models.signal_entity import SignalEntity
from backend.models.signal_score import SignalScore
from backend.models.subscription import Subscription
from backend.models.user import User
from backend.models.user_feedback import UserFeedback

__all__ = [
    "Base",
    "Organization",
    "User",
    "OrgUser",
    "Document",
    "AIJob",
    "AIUsageLog",
    "Subscription",
    "AuditLog",
    "APIKey",
    # Phase 3 — Signal Intelligence
    "Industry",
    "Entity",
    "SignalContract",
    "Signal",
    "SignalEntity",
    "IntelligenceBrief",
    "BriefSignal",
    "ChatSession",
    "ChatMessage",
    "SearchQuery",
    "Recommendation",
    "MLModelRun",
    "MLModelRegistry",
    "SignalScore",
    # Intelligence Moat — Entity Resolution 2.0
    "EntityAlias",
    "EntitySourceProfile",
    "EntityRelationship",
    # Intelligence Moat — Causal Intelligence
    "CausalEvent",
    "CausalEdge",
    # Intelligence Moat — Feedback Loop
    "UserFeedback",
    # Intelligence Moat — Metrics
    "MoatMetricSnapshot",
    # Regulatory Knowledge
    "RegulatoryEvent",
    "RegulatoryRule",
    "RegulatoryImpact",
    "RegulatoryPattern",
    # Pricing & Feature Gating
    "BetaAccount",
    "CreditTransaction",
    "FeatureGate",
    "PricingConfig",
]
