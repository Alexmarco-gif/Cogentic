"""Web Search Provider abstraction layer.

Pluggable architecture for live web search during on-demand queries.
Providers: SerpApi (default), with room for Google, Bing, Brave, Tavily, etc.

Usage:
    from backend.services.web_search import get_web_search_provider

    provider = get_web_search_provider()
    results = await provider.search("fintech regulation Nigeria 2026")
"""

from backend.services.web_search.base import (
    WebSearchError,
    WebSearchProvider,
    WebSearchResult,
)
from backend.services.web_search.cache import WebSearchCache
from backend.services.web_search.factory import get_web_search_provider

__all__ = [
    "WebSearchProvider",
    "WebSearchResult",
    "WebSearchError",
    "WebSearchCache",
    "get_web_search_provider",
]
