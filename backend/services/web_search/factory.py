"""Web search provider factory.

Returns the configured web search provider based on settings.
Supports multiple providers with fallback chain.

Usage:
    provider = get_web_search_provider()         # Default (SerpApi)
    provider = get_web_search_provider("serpapi") # Explicit
"""

import logging

from backend.config import get_settings
from backend.services.web_search.base import WebSearchProvider

logger = logging.getLogger(__name__)

# Singleton cache
_providers: dict[str, WebSearchProvider] = {}


def get_web_search_provider(
    provider_name: str | None = None,
) -> WebSearchProvider:
    """Get or create a web search provider singleton.

    Args:
        provider_name: Provider name override. If None, uses settings.
                       Supported: "serpapi" (more can be added).

    Returns:
        WebSearchProvider instance.

    Raises:
        ValueError: If the provider name is not recognized.
    """
    settings = get_settings()
    name = (provider_name or settings.web_search_provider).lower()

    if name in _providers:
        return _providers[name]

    if name == "serpapi":
        from backend.services.web_search.serpapi_provider import SerpApiProvider

        provider = SerpApiProvider(api_key=settings.serpapi_api_key)
    elif name == "none":
        # Null provider — returns empty results (for testing / disabled search)
        provider = _NullSearchProvider()
    else:
        raise ValueError(
            f"Unknown web search provider: '{name}'. " f"Supported: serpapi, none"
        )

    _providers[name] = provider
    logger.info(f"Initialized web search provider: {name}")
    return provider


class _NullSearchProvider(WebSearchProvider):
    """No-op provider for when web search is disabled."""

    provider_name = "none"

    async def search(self, query, **kwargs):  # type: ignore[override]
        return []

    async def news_search(self, query, **kwargs):  # type: ignore[override]
        return []

    async def is_available(self) -> bool:
        return False
