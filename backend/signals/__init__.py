"""Signal Acquisition Pipeline.

Fetchers, processors, and scheduler for 280 signal contracts.
Pipeline: Contract -> Scheduler -> Fetcher -> Dedup -> Extract -> Store
"""

from backend.signals.fetchers import get_fetcher
from backend.signals.processors import DedupProcessor, ExtractorProcessor
from backend.signals.scheduler import SignalScheduler, get_scheduler

__all__ = [
    "get_fetcher",
    "DedupProcessor",
    "ExtractorProcessor",
    "SignalScheduler",
    "get_scheduler",
]
