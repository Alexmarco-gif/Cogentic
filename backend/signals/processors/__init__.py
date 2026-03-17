"""Signal Processors — Extraction, Dedup, Scoring"""

from backend.signals.processors.dedup import DedupProcessor
from backend.signals.processors.extractor import ExtractorProcessor

__all__ = [
    "DedupProcessor",
    "ExtractorProcessor",
]
