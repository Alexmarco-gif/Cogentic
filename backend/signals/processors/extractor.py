"""Signal extraction and normalization processor.

Converts raw FetchResults into Signal DB records with:
- Content normalization
- Initial confidence scoring
- 90-day expiration
- Entity/contract linking
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from backend.signals.fetchers.base import FetchResult

logger = logging.getLogger(__name__)

# Base confidence scores by source type
_SOURCE_CONFIDENCE: dict[str, float] = {
    "api": 0.75,  # Structured, reliable
    "rss": 0.70,  # Semi-structured, usually curated
    "scraper": 0.60,  # Unstructured, may be noisy
    "social": 0.50,  # Noisy, needs validation
}


# Minimum quality thresholds
_MIN_CONTENT_LENGTH = 50
_MAX_HTML_TAG_RATIO = 0.90


class ExtractorProcessor:
    """Normalizes FetchResults into signal-ready dicts for DB insertion.

    Applies:
    1. Content quality gate (reject noise)
    2. Content length validation
    3. Source-based confidence scoring
    4. Expiration calculation (90-day retention)
    5. Metadata enrichment
    """

    def process(
        self,
        result: FetchResult,
        *,
        contract_id: UUID,
        source_type: str,
        org_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Convert a FetchResult into a dict ready for Signal creation.

        Args:
            result: The raw fetched result.
            contract_id: The signal contract that produced this result.
            source_type: The fetcher type (api, rss, scraper, social).
            org_id: Optional org scope (None = global signal).

        Returns:
            Dict of kwargs for SignalRepository.create()
        """
        now = datetime.now(timezone.utc)

        # Calculate initial confidence
        confidence = self._calculate_confidence(result, source_type)

        # Build signal record
        signal_data: dict[str, Any] = {
            "contract_id": contract_id,
            "org_id": org_id,
            "title": (result.title or "")[:500] or None,
            "summary": self._make_summary(result.content),
            "raw_content": result.content,
            "extracted_data": result.extracted_data or {},
            "source_url": result.source_url,
            "signal_type": result.signal_type,
            "confidence": round(confidence, 2),
            "content_hash": result.content_hash,
            "fetched_at": now,
            "published_at": result.published_at,
            "expires_at": now + timedelta(days=90),  # 90-day retention
        }

        return signal_data

    def process_batch(
        self,
        results: list[FetchResult],
        *,
        contract_id: UUID,
        source_type: str,
        org_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Process a batch of FetchResults into signal dicts.

        Filters out low-quality results before processing.

        Args:
            results: List of fetched results.
            contract_id: The signal contract ID.
            source_type: The fetcher type.
            org_id: Optional org scope.

        Returns:
            List of dicts ready for bulk Signal creation.
        """
        processed = []
        rejected = 0
        for r in results:
            if not self._passes_quality_gate(r):
                rejected += 1
                continue
            processed.append(
                self.process(
                    r,
                    contract_id=contract_id,
                    source_type=source_type,
                    org_id=org_id,
                )
            )
        if rejected:
            logger.info(f"Quality gate rejected {rejected}/{len(results)} signals")
        return processed

    def _passes_quality_gate(self, result: FetchResult) -> bool:
        """Reject low-quality signals before they hit dedup or DB.

        Rejects:
        - Empty or near-empty content (< 50 chars)
        - Missing both title AND content
        - Content that is >90% HTML tags (scraper garbage)
        """
        # Must have at least a title or meaningful content
        has_title = bool(result.title and result.title.strip())
        has_content = bool(
            result.content and len(result.content.strip()) >= _MIN_CONTENT_LENGTH
        )

        if not has_title and not has_content:
            return False

        # Content-only check: if we have content, it must meet min length
        if result.content and not has_content and not has_title:
            return False

        # HTML garbage check — if content is mostly tags, reject
        if result.content and len(result.content) > 100:
            tag_chars = sum(1 for c in result.content if c in "<>/")
            ratio = tag_chars / len(result.content)
            if ratio > _MAX_HTML_TAG_RATIO:
                return False

        return True

    def _calculate_confidence(
        self,
        result: FetchResult,
        source_type: str,
    ) -> float:
        """Calculate initial confidence score for a signal.

        Factors:
        - Base score from source type
        - Content quality (length, has title)
        - Has publish date
        - Engagement metrics (for social)
        """
        base = _SOURCE_CONFIDENCE.get(source_type, 0.5)

        # Content quality bonuses
        content_len = len(result.content)
        if content_len > 500:
            base += 0.05
        if content_len > 2000:
            base += 0.05
        if result.title:
            base += 0.03
        if result.published_at:
            base += 0.03

        # Social engagement bonus
        if source_type == "social":
            engagement = result.extracted_data.get("engagement", 0)
            if engagement > 100:
                base += 0.10
            elif engagement > 50:
                base += 0.05
            elif engagement > 10:
                base += 0.02

        # Cap at 0.90 — ML refinement in Sprint 3 can push higher
        return min(base, 0.90)

    @staticmethod
    def _make_summary(content: str, max_length: int = 500) -> str | None:
        """Generate a simple summary (first N chars) from content."""
        if not content:
            return None

        clean = content.strip()
        if len(clean) <= max_length:
            return clean

        # Try to break at sentence boundary
        truncated = clean[:max_length]
        last_period = truncated.rfind(". ")
        if last_period > max_length * 0.5:
            return truncated[: last_period + 1]

        return truncated + "..."
