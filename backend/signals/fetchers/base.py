"""Base fetcher interface for signal acquisition.

All fetcher types (API, Scraper, RSS, Social) inherit from BaseFetcher
and implement the `fetch()` method.
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Normalized result from any fetcher type.

    Every fetcher returns a list of FetchResults regardless of source type.
    These are then processed through extraction and dedup before becoming Signals.
    """

    title: str
    content: str
    source_url: str
    published_at: datetime | None = None
    signal_type: str = "news"  # news, social, regulatory, financial, market, technology
    extracted_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str | None = None

    def __post_init__(self):
        """Compute content hash if not provided."""
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(
                self._normalize(self.content).encode("utf-8")
            ).hexdigest()

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize whitespace for stable hashing across sources."""
        return " ".join(text.split()).strip().lower()


@dataclass
class FetchError:
    """Error details from a failed fetch attempt."""

    message: str
    status_code: int | None = None
    retryable: bool = True


class BaseFetcher(ABC):
    """Abstract base for all signal fetchers.

    Each fetcher gets an httpx.AsyncClient for connection pooling
    and respects rate limits defined in the signal contract.
    """

    # Subclasses should set this
    source_type: str = "unknown"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self._owns_client = client is None
        self._custom_timeout: float | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with optional custom timeout."""
        if self._client is None:
            timeout_val = self._custom_timeout or 30.0
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_val, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": "ESIP/1.0 (Signal Intelligence Platform)"},
            )
        return self._client

    def configure_timeout(self, extraction_config: dict[str, Any]) -> None:
        """Apply per-contract timeout from extraction_config if present."""
        custom = extraction_config.get("timeout")
        if custom and isinstance(custom, (int, float)) and custom > 0:
            self._custom_timeout = float(custom)

    async def close(self):
        """Close owned HTTP client."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def fetch(
        self,
        source_url: str,
        extraction_config: dict[str, Any],
    ) -> list[FetchResult] | FetchError:
        """Fetch signals from the source.

        Args:
            source_url: The URL to fetch from.
            extraction_config: Source-specific extraction rules
                (JSON paths, CSS selectors, API params, etc.)

        Returns:
            List of FetchResult on success, or FetchError on failure.
        """
        ...

    def _make_hash(self, content: str) -> str:
        """SHA-256 hash for deduplication (whitespace-normalized)."""
        normalized = " ".join(content.split()).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _safe_parse_date(self, date_str: str | None) -> datetime | None:
        """Try to parse a date string, return None on failure."""
        if not date_str:
            return None
        # Try common formats
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
            "%a, %d %b %Y %H:%M:%S GMT",
        ):
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        logger.debug(f"Could not parse date: {date_str}")
        return None
