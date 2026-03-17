"""Base interface for web search providers.

All providers (SerpApi, Google, Bing, Brave, etc.) implement
WebSearchProvider and return normalized WebSearchResult objects.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SearchEngine(str, Enum):
    """Supported search engines within providers."""

    GOOGLE = "google"
    BING = "bing"
    GOOGLE_NEWS = "google_news"
    GOOGLE_SCHOLAR = "google_scholar"
    YAHOO = "yahoo"
    DUCKDUCKGO = "duckduckgo"


@dataclass
class WebSearchResult:
    """Normalized result from any web search provider.

    Regardless of which provider or engine is used, all results
    are normalized into this structure before entering the pipeline.
    """

    title: str
    snippet: str
    url: str
    source: str  # e.g. "serpapi:google", "serpapi:google_news"
    position: int = 0  # rank position in original results
    published_at: datetime | None = None
    thumbnail_url: str | None = None
    cached_page_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Scores assigned during fusion with internal signals
    relevance_score: float = 0.0  # Set during ranking (0.0-1.0)
    confidence: float = 0.65  # Base confidence for web results

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON/cache storage."""
        return {
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
            "source": self.source,
            "position": self.position,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "thumbnail_url": self.thumbnail_url,
            "relevance_score": self.relevance_score,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class WebSearchError:
    """Error from a web search provider."""

    message: str
    provider: str
    status_code: int | None = None
    retryable: bool = True


class WebSearchProvider(ABC):
    """Abstract base for all web search providers.

    Each provider must implement:
      - search():       General web search
      - news_search():  News-specific search
      - is_available():  Health check / API key validation

    Optionally:
      - scholar_search(): Academic search
      - image_search():   Image search
    """

    provider_name: str = "unknown"

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        country: str | None = None,
        language: str | None = None,
        time_range: str | None = None,
        safe_search: bool = True,
        engine: SearchEngine = SearchEngine.GOOGLE,
    ) -> list[WebSearchResult] | WebSearchError:
        """Execute a general web search.

        Args:
            query: Search query string.
            num_results: Max results to return (1-100).
            country: Country code for localized results (e.g., "ng", "us", "gb").
            language: Language code (e.g., "en", "fr").
            time_range: Time filter — "hour", "day", "week", "month", "year".
            safe_search: Enable safe search filtering.
            engine: Which search engine to use.

        Returns:
            List of WebSearchResult or WebSearchError.
        """
        ...

    @abstractmethod
    async def news_search(
        self,
        query: str,
        *,
        num_results: int = 10,
        country: str | None = None,
        language: str | None = None,
        time_range: str | None = None,
    ) -> list[WebSearchResult] | WebSearchError:
        """Execute a news-specific search.

        Returns fresher, news-oriented results from Google News or equivalent.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is configured and reachable.

        Returns True if the API key is set and a simple request succeeds.
        """
        ...

    async def scholar_search(
        self,
        query: str,
        *,
        num_results: int = 10,
    ) -> list[WebSearchResult] | WebSearchError:
        """Academic/scholarly search (optional, not all providers support)."""
        return WebSearchError(
            message=f"Scholar search not supported by {self.provider_name}",
            provider=self.provider_name,
            retryable=False,
        )

    async def close(self) -> None:
        """Clean up resources (HTTP clients, etc.)."""
        pass
