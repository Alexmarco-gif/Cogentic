"""Signal Fetchers — API, Scraper, RSS, Social.

Factory function `get_fetcher()` returns the correct fetcher
for a given signal contract's source_type.
"""

from backend.signals.fetchers.api_fetcher import APIFetcher
from backend.signals.fetchers.base import BaseFetcher, FetchError, FetchResult
from backend.signals.fetchers.rss_fetcher import RSSFetcher
from backend.signals.fetchers.scraper_fetcher import ScraperFetcher
from backend.signals.fetchers.social_fetcher import SocialFetcher

_FETCHER_MAP: dict[str, type[BaseFetcher]] = {
    "api": APIFetcher,
    "rss": RSSFetcher,
    "scraper": ScraperFetcher,
    "social": SocialFetcher,
}


def get_fetcher(source_type: str) -> BaseFetcher:
    """Factory: return the appropriate fetcher for a source type.

    Args:
        source_type: One of "api", "rss", "scraper", "social"

    Returns:
        An instance of the corresponding fetcher.

    Raises:
        ValueError: If source_type is not recognized.
    """
    fetcher_cls = _FETCHER_MAP.get(source_type)
    if fetcher_cls is None:
        raise ValueError(
            f"Unknown source_type '{source_type}'. "
            f"Supported: {', '.join(_FETCHER_MAP.keys())}"
        )
    return fetcher_cls()


__all__ = [
    "BaseFetcher",
    "FetchResult",
    "FetchError",
    "APIFetcher",
    "RSSFetcher",
    "ScraperFetcher",
    "SocialFetcher",
    "get_fetcher",
]
