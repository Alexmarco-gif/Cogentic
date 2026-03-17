"""SerpApi web search provider.

Uses SerpApi (https://serpapi.com) to query Google, Google News,
Google Scholar, Bing, and other engines via a single API key.

SerpApi handles proxy rotation, CAPTCHA solving, and returns
structured JSON — ideal for a production signal intelligence platform.

Rate limits (default plan): 100 searches/month (free), 5000/month (developer).
Production plans: 15,000+/month.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config import get_settings
from backend.services.web_search.base import (
    SearchEngine,
    WebSearchError,
    WebSearchProvider,
    WebSearchResult,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# SerpApi base URL
SERPAPI_BASE_URL = "https://serpapi.com/search"

# Map our SearchEngine enum to SerpApi engine parameter values
_ENGINE_MAP: dict[SearchEngine, str] = {
    SearchEngine.GOOGLE: "google",
    SearchEngine.BING: "bing",
    SearchEngine.GOOGLE_NEWS: "google_news",
    SearchEngine.GOOGLE_SCHOLAR: "google_scholar",
    SearchEngine.YAHOO: "yahoo",
    SearchEngine.DUCKDUCKGO: "duckduckgo",
}

# SerpApi time range → tbs parameter mapping (Google)
_TIME_RANGE_MAP: dict[str, str] = {
    "hour": "qdr:h",
    "day": "qdr:d",
    "week": "qdr:w",
    "month": "qdr:m",
    "year": "qdr:y",
}


class SerpApiProvider(WebSearchProvider):
    """Web search provider using SerpApi.

    Supports multiple search engines through a single API:
      - Google Web Search (default)
      - Google News (news_search)
      - Google Scholar (scholar_search)
      - Bing, Yahoo, DuckDuckGo

    All results are normalized into WebSearchResult objects.
    """

    provider_name = "serpapi"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.serpapi_api_key
        self._client: httpx.AsyncClient | None = None
        self._concurrency = asyncio.Semaphore(settings.serpapi_max_concurrent_requests)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.serpapi_timeout_seconds, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": "Cogent/1.0 (Signal Intelligence Platform)"},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Check if SerpApi is configured and reachable."""
        if not self._api_key:
            return False
        try:
            client = await self._get_client()
            response = await client.get(
                "https://serpapi.com/account",
                params={"api_key": self._api_key},
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"SerpApi availability check failed: {e}")
            return False

    # ── General Web Search ───────────────────────────────────────────

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
        """Execute a web search via SerpApi."""
        if not self._api_key:
            return WebSearchError(
                message="SerpApi API key not configured. Set SERPAPI_API_KEY.",
                provider=self.provider_name,
                retryable=False,
            )

        serpapi_engine = _ENGINE_MAP.get(engine, "google")

        params: dict[str, Any] = {
            "api_key": self._api_key,
            "engine": serpapi_engine,
            "q": query,
            "num": min(num_results, 100),
            "output": "json",
        }

        if country:
            params["gl"] = country  # e.g. "ng", "us", "gb"
        if language:
            params["hl"] = language  # e.g. "en", "fr"
        if time_range and time_range in _TIME_RANGE_MAP:
            params["tbs"] = _TIME_RANGE_MAP[time_range]
        if safe_search:
            params["safe"] = "active"

        return await self._execute_search(
            params, f"{self.provider_name}:{serpapi_engine}"
        )

    # ── News Search ──────────────────────────────────────────────────

    async def news_search(
        self,
        query: str,
        *,
        num_results: int = 10,
        country: str | None = None,
        language: str | None = None,
        time_range: str | None = None,
    ) -> list[WebSearchResult] | WebSearchError:
        """Execute a Google News search via SerpApi."""
        if not self._api_key:
            return WebSearchError(
                message="SerpApi API key not configured. Set SERPAPI_API_KEY.",
                provider=self.provider_name,
                retryable=False,
            )

        params: dict[str, Any] = {
            "api_key": self._api_key,
            "engine": "google_news",
            "q": query,
            "output": "json",
        }

        if country:
            params["gl"] = country
        if language:
            params["hl"] = language
        if time_range:
            # Google News uses "when" parameter
            _news_time_map = {
                "hour": "1h",
                "day": "1d",
                "week": "7d",
                "month": "1m",
                "year": "1y",
            }
            if time_range in _news_time_map:
                params["when"] = _news_time_map[time_range]

        return await self._execute_search(
            params, f"{self.provider_name}:google_news", is_news=True
        )

    # ── Scholar Search ───────────────────────────────────────────────

    async def scholar_search(
        self,
        query: str,
        *,
        num_results: int = 10,
    ) -> list[WebSearchResult] | WebSearchError:
        """Execute a Google Scholar search via SerpApi."""
        if not self._api_key:
            return WebSearchError(
                message="SerpApi API key not configured. Set SERPAPI_API_KEY.",
                provider=self.provider_name,
                retryable=False,
            )

        params: dict[str, Any] = {
            "api_key": self._api_key,
            "engine": "google_scholar",
            "q": query,
            "num": min(num_results, 20),
            "output": "json",
        }

        return await self._execute_search(
            params, f"{self.provider_name}:google_scholar", is_scholar=True
        )

    # ── Multi-Engine Parallel Search ─────────────────────────────────

    async def multi_search(
        self,
        query: str,
        *,
        engines: list[str] | None = None,
        num_results_per_engine: int = 5,
        country: str | None = None,
        language: str | None = None,
        time_range: str | None = None,
    ) -> dict[str, list[WebSearchResult] | WebSearchError]:
        """Search across multiple engines in parallel and return fused results.

        This is the power feature: query Google + Google News + Bing
        simultaneously and get a unified, deduplicated view.

        Args:
            query: Search query.
            engines: List of engine names. Defaults to ["google", "google_news"].
            num_results_per_engine: Results per engine.
            country: Country code.
            language: Language code.
            time_range: Time filter.

        Returns:
            Dict mapping engine name to results or error.
        """
        if engines is None:
            engines = ["google", "google_news"]

        engine_map_rev = {v: k for k, v in _ENGINE_MAP.items()}
        tasks = {}

        for eng_name in engines:
            engine_enum = engine_map_rev.get(eng_name)
            if eng_name == "google_news":
                tasks[eng_name] = self.news_search(
                    query,
                    num_results=num_results_per_engine,
                    country=country,
                    language=language,
                    time_range=time_range,
                )
            elif eng_name == "google_scholar":
                tasks[eng_name] = self.scholar_search(
                    query,
                    num_results=num_results_per_engine,
                )
            elif engine_enum:
                tasks[eng_name] = self.search(
                    query,
                    num_results=num_results_per_engine,
                    country=country,
                    language=language,
                    time_range=time_range,
                    engine=engine_enum,
                )
            else:
                tasks[eng_name] = asyncio.coroutine(
                    lambda: WebSearchError(
                        message=f"Unknown engine: {eng_name}",
                        provider=self.provider_name,
                        retryable=False,
                    )
                )()

        results_raw = await asyncio.gather(*tasks.values(), return_exceptions=True)

        results: dict[str, list[WebSearchResult] | WebSearchError] = {}
        for eng_name, result in zip(tasks.keys(), results_raw):
            if isinstance(result, Exception):
                results[eng_name] = WebSearchError(
                    message=str(result),
                    provider=self.provider_name,
                    retryable=True,
                )
            else:
                results[eng_name] = result

        return results

    # ── Core Execution ───────────────────────────────────────────────

    async def _execute_search(
        self,
        params: dict[str, Any],
        source_label: str,
        *,
        is_news: bool = False,
        is_scholar: bool = False,
    ) -> list[WebSearchResult] | WebSearchError:
        """Execute a SerpApi search request with retry, rate limiting, and caching.

        Cache layer sits in front of the API call to reduce SerpApi costs.
        Results are cached per query+engine with TTL from settings.
        """
        # ── Cache check ──────────────────────────────────────────────
        query_text = params.get("q", "")
        engine_name = params.get("engine", "google")

        try:
            from backend.services.web_search.cache import WebSearchCache

            cache = WebSearchCache()
            cached = await cache.get(query_text, engine_name)
            if cached is not None:
                logger.info(
                    f"SerpApi cache hit for '{query_text[:40]}…' "
                    f"engine={engine_name} ({len(cached)} results)"
                )
                return cached
        except Exception as e:
            logger.debug(f"Web search cache read skipped: {e}")

        # ── API call ─────────────────────────────────────────────────
        max_retries = 2

        for attempt in range(max_retries):
            try:
                async with self._concurrency:
                    client = await self._get_client()
                    response = await client.get(SERPAPI_BASE_URL, params=params)

                if response.status_code == 429:
                    # Rate limited — wait and retry
                    if attempt < max_retries - 1:
                        delay = 2 ** (attempt + 1)
                        logger.warning(f"SerpApi rate limited, retrying in {delay}s")
                        await asyncio.sleep(delay)
                        continue
                    return WebSearchError(
                        message="SerpApi rate limit exceeded",
                        provider=self.provider_name,
                        status_code=429,
                        retryable=True,
                    )

                if response.status_code != 200:
                    error_msg = response.text[:200]
                    return WebSearchError(
                        message=f"SerpApi HTTP {response.status_code}: {error_msg}",
                        provider=self.provider_name,
                        status_code=response.status_code,
                        retryable=response.status_code >= 500,
                    )

                data = response.json()

                # Check for SerpApi-level errors
                if "error" in data:
                    return WebSearchError(
                        message=f"SerpApi error: {data['error']}",
                        provider=self.provider_name,
                        retryable=False,
                    )

                # Parse based on search type
                if is_news:
                    parsed = self._parse_news_results(data, source_label)
                elif is_scholar:
                    parsed = self._parse_scholar_results(data, source_label)
                else:
                    parsed = self._parse_organic_results(data, source_label)

                # ── Cache write ───────────────────────────────────────
                if isinstance(parsed, list) and parsed:
                    try:
                        from backend.services.web_search.cache import WebSearchCache

                        cache = WebSearchCache()
                        await cache.set(query_text, engine_name, parsed)
                    except Exception as e:
                        logger.debug(f"Web search cache write skipped: {e}")

                return parsed

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"SerpApi timeout (attempt {attempt + 1}), retrying..."
                    )
                    await asyncio.sleep(2**attempt)
                    continue
                return WebSearchError(
                    message=f"SerpApi timeout after {max_retries} attempts",
                    provider=self.provider_name,
                    retryable=True,
                )
            except httpx.RequestError as e:
                return WebSearchError(
                    message=f"SerpApi request error: {e}",
                    provider=self.provider_name,
                    retryable=True,
                )
            except Exception as e:
                logger.error(f"SerpApi unexpected error: {e}", exc_info=True)
                return WebSearchError(
                    message=f"SerpApi unexpected error: {e}",
                    provider=self.provider_name,
                    retryable=False,
                )

        return WebSearchError(
            message="SerpApi: all retries exhausted",
            provider=self.provider_name,
            retryable=False,
        )

    # ── Response Parsers ─────────────────────────────────────────────

    def _parse_organic_results(
        self,
        data: dict[str, Any],
        source_label: str,
    ) -> list[WebSearchResult]:
        """Parse standard Google/Bing organic search results."""
        results: list[WebSearchResult] = []
        organic = data.get("organic_results", [])

        for item in organic:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            url = item.get("link", "")

            if not url:
                continue

            # Try to extract date
            published_at = self._parse_date(item.get("date"))

            results.append(
                WebSearchResult(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source=source_label,
                    position=item.get("position", len(results) + 1),
                    published_at=published_at,
                    thumbnail_url=item.get("thumbnail"),
                    cached_page_url=item.get("cached_page_link"),
                    metadata={
                        "displayed_link": item.get("displayed_link", ""),
                        "snippet_highlighted_words": item.get(
                            "snippet_highlighted_words", []
                        ),
                        "rich_snippet": item.get("rich_snippet"),
                        "sitelinks": item.get("sitelinks"),
                    },
                )
            )

        # Also grab knowledge graph if present (often has high-quality data)
        knowledge_graph = data.get("knowledge_graph")
        if knowledge_graph and knowledge_graph.get("title"):
            kg_snippet = knowledge_graph.get("description", "")
            kg_url = knowledge_graph.get("website") or knowledge_graph.get(
                "source", {}
            ).get("link", "")
            if kg_url:
                results.insert(
                    0,
                    WebSearchResult(
                        title=knowledge_graph["title"],
                        snippet=kg_snippet,
                        url=kg_url,
                        source=f"{source_label}:knowledge_graph",
                        position=0,
                        metadata={
                            "type": "knowledge_graph",
                            "entity_type": knowledge_graph.get("type"),
                            "attributes": {
                                k: v
                                for k, v in knowledge_graph.items()
                                if k
                                not in (
                                    "title",
                                    "description",
                                    "website",
                                    "source",
                                    "type",
                                )
                                and isinstance(v, (str, int, float))
                            },
                        },
                        confidence=0.80,  # Knowledge graph is higher quality
                    ),
                )

        logger.info(f"SerpApi organic search returned {len(results)} results")
        return results

    def _parse_news_results(
        self,
        data: dict[str, Any],
        source_label: str,
    ) -> list[WebSearchResult]:
        """Parse Google News results from SerpApi."""
        results: list[WebSearchResult] = []
        news_results = data.get("news_results", [])

        for item in news_results:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            url = item.get("link", "")

            if not url:
                continue

            published_at = self._parse_date(item.get("date"))

            results.append(
                WebSearchResult(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source=source_label,
                    position=item.get("position", len(results) + 1),
                    published_at=published_at,
                    thumbnail_url=item.get("thumbnail"),
                    metadata={
                        "news_source": item.get("source", {}).get("name", ""),
                        "news_source_icon": item.get("source", {}).get("icon", ""),
                        "stories": [
                            {
                                "title": s.get("title", ""),
                                "link": s.get("link", ""),
                                "source": s.get("source", {}).get("name", ""),
                                "date": s.get("date", ""),
                            }
                            for s in item.get("stories", [])[:3]
                        ],
                    },
                    confidence=0.70,  # News results slightly higher confidence
                )
            )

        logger.info(f"SerpApi news search returned {len(results)} results")
        return results

    def _parse_scholar_results(
        self,
        data: dict[str, Any],
        source_label: str,
    ) -> list[WebSearchResult]:
        """Parse Google Scholar results from SerpApi."""
        results: list[WebSearchResult] = []
        organic = data.get("organic_results", [])

        for item in organic:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            url = item.get("link", "")

            if not url:
                continue

            # Scholar has citation info
            inline_links = item.get("inline_links", {})
            cited_by = inline_links.get("cited_by", {})
            cited_count = cited_by.get("total", 0)

            results.append(
                WebSearchResult(
                    title=title,
                    snippet=snippet,
                    url=url,
                    source=source_label,
                    position=item.get("position", len(results) + 1),
                    published_at=self._parse_date(
                        item.get("publication_info", {}).get("summary", "")
                    ),
                    metadata={
                        "cited_by_count": cited_count,
                        "publication_info": item.get("publication_info", {}).get(
                            "summary", ""
                        ),
                        "resource_type": item.get("type", ""),
                        "resources": [
                            {"title": r.get("title", ""), "link": r.get("link", "")}
                            for r in item.get("resources", [])[:2]
                        ],
                    },
                    confidence=0.75,  # Scholar results are higher quality
                )
            )

        logger.info(f"SerpApi scholar search returned {len(results)} results")
        return results

    # ── Utilities ────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        """Best-effort date parsing from SerpApi date strings."""
        if not date_str:
            return None

        # SerpApi returns dates like "2 days ago", "Jan 15, 2026", etc.
        date_str = str(date_str).strip()

        # Try relative dates ("X hours/days/weeks ago")
        import re

        relative_match = re.match(
            r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago",
            date_str,
            re.IGNORECASE,
        )
        if relative_match:
            from datetime import timedelta

            amount = int(relative_match.group(1))
            unit = relative_match.group(2).lower()
            delta_map = {
                "minute": timedelta(minutes=amount),
                "hour": timedelta(hours=amount),
                "day": timedelta(days=amount),
                "week": timedelta(weeks=amount),
                "month": timedelta(days=amount * 30),
                "year": timedelta(days=amount * 365),
            }
            delta = delta_map.get(unit)
            if delta:
                return datetime.now(timezone.utc) - delta

        # Try standard date formats
        from dateutil import parser as dateutil_parser

        try:
            parsed = dateutil_parser.parse(date_str, fuzzy=True)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, OverflowError):
            return None
