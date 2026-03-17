"""Data access repositories"""

from backend.repositories.chat_session import ChatSessionRepository
from backend.repositories.entity import EntityRepository
from backend.repositories.industry import IndustryRepository
from backend.repositories.intelligence_brief import IntelligenceBriefRepository
from backend.repositories.ml_model_run import MLModelRunRepository
from backend.repositories.search_query import SearchQueryRepository
from backend.repositories.signal import SignalRepository
from backend.repositories.signal_contract import SignalContractRepository
from backend.repositories.signal_score import SignalScoreRepository

__all__ = [
    # Phase 3 — Signal Intelligence
    "IndustryRepository",
    "EntityRepository",
    "SignalContractRepository",
    "SignalRepository",
    "IntelligenceBriefRepository",
    "ChatSessionRepository",
    "SearchQueryRepository",
    "MLModelRunRepository",
    "SignalScoreRepository",
]
