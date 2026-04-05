"""API Fetcher — fetches signals from REST APIs.

Handles JSON responses from news APIs (NewsAPI, Bing News),
financial data APIs, and any REST endpoint defined in a signal contract.

~40% of all signals come through API fetching.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.signals.fetchers.base import BaseFetcher, FetchError, FetchResult
from backend.signals.provider_presets import resolve_api_provider_config

logger = logging.getLogger(__name__)


class APIFetcher(BaseFetcher):
    """Fetches signals from REST API endpoints.

    extraction_config schema:
    {
        "method": "GET",                    # HTTP method
        "headers": {"Authorization": "..."}, # Extra headers
        "params": {"q": "...", "pageSize": 10},  # Query params
        "results_path": "articles",         # JSON path to results array
        "title_path": "title",              # Path to title in each result
        "content_path": "description",      # Path to content
        "url_path": "url",                  # Path to source URL
        "date_path": "publishedAt",         # Path to publish date
        "signal_type": "news",              # Signal classification
        "extra_fields": ["author", "source.name"]  # Additional fields to extract
    }
    """

    source_type = "api"

    async def fetch(
        self,
        source_url: str,
        extraction_config: dict[str, Any],
    ) -> list[FetchResult] | FetchError:
        """Fetch signals from a REST API endpoint."""
        source_url, extraction_config = resolve_api_provider_config(
            source_url, extraction_config
        )
        provider = str(extraction_config.get("provider", "generic")).lower()
        if provider == "newsapi" and not extraction_config.get("params", {}).get(
            "apiKey"
        ):
            return FetchError(
                message="NEWSAPI_API_KEY is not configured for NewsAPI contracts",
                retryable=False,
            )
        if provider == "ngx_market_data":
            has_api_key = bool(
                extraction_config.get("headers", {}).get("X-API-Key")
                or extraction_config.get("params", {}).get("api_key")
                or extraction_config.get("auth", {}).get("api_key")
            )
            if not has_api_key:
                return FetchError(
                    message="NGX_MARKET_DATA_API_KEY is not configured for NGX contracts",
                    retryable=False,
                )
        if not source_url:
            return FetchError(
                message="API source URL is not configured for this contract",
                retryable=False,
            )
        self.configure_timeout(extraction_config)
        client = await self._get_client()

        method = extraction_config.get("method", "GET").upper()
        headers = extraction_config.get("headers", {})
        params = extraction_config.get("params", {})
        max_retries = extraction_config.get("retries", 3)

        last_error: FetchError | None = None

        for attempt in range(max_retries):
            try:
                if method == "GET":
                    response = await client.get(
                        source_url, headers=headers, params=params
                    )
                elif method == "POST":
                    body = extraction_config.get("body", {})
                    response = await client.post(
                        source_url, headers=headers, params=params, json=body
                    )
                else:
                    return FetchError(
                        message=f"Unsupported HTTP method: {method}",
                        retryable=False,
                    )

                response.raise_for_status()
                data = response.json()
                return self._parse_response(data, extraction_config, source_url)

            except httpx.TimeoutException:
                last_error = FetchError(
                    message=f"Timeout fetching {source_url} (attempt {attempt + 1}/{max_retries})",
                    retryable=True,
                )
            except httpx.HTTPStatusError as e:
                retryable = (
                    e.response.status_code >= 500 or e.response.status_code == 429
                )
                last_error = FetchError(
                    message=f"HTTP {e.response.status_code} from {source_url}",
                    status_code=e.response.status_code,
                    retryable=retryable,
                )
                if not retryable:
                    return last_error
            except httpx.RequestError as e:
                last_error = FetchError(
                    message=f"Request error fetching {source_url}: {e}",
                    retryable=True,
                )
            except Exception as e:
                return FetchError(
                    message=f"Unexpected error fetching {source_url}: {e}",
                    retryable=False,
                )

            # Exponential backoff: 1s, 2s, 4s
            if attempt < max_retries - 1:
                import asyncio

                delay = 2**attempt
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} for {source_url} in {delay}s"
                )
                await asyncio.sleep(delay)

        return last_error or FetchError(
            message=f"All {max_retries} retries failed for {source_url}",
            retryable=False,
        )

    def _parse_response(
        self,
        data: Any,
        config: dict[str, Any],
        fallback_url: str,
    ) -> list[FetchResult]:
        """Parse API response into FetchResults."""
        provider = str(config.get("provider", "generic")).lower()
        if provider == "ngx_market_data":
            return self._parse_ngx_market_response(data, config, fallback_url)

        results_path = config.get("results_path", "")
        title_path = config.get("title_path", "title")
        content_path = config.get("content_path", "description")
        url_path = config.get("url_path", "url")
        date_path = config.get("date_path", "publishedAt")
        signal_type = config.get("signal_type", "news")
        extra_fields = config.get("extra_fields", [])

        # Navigate to results array
        items = self._navigate_path(data, results_path)
        if not isinstance(items, list):
            items = [items] if items else []

        fetch_results: list[FetchResult] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            title = self._navigate_path(item, title_path) or ""
            content = self._navigate_path(item, content_path) or ""
            source_url = self._navigate_path(item, url_path) or fallback_url
            date_str = self._navigate_path(item, date_path)

            # Skip empty items
            if not title and not content:
                continue

            # Truncate content to reasonable size
            if len(content) > 10000:
                content = content[:10000]

            # Extract extra fields
            extracted = {}
            for field_path in extra_fields:
                value = self._navigate_path(item, field_path)
                if value is not None:
                    key = field_path.split(".")[-1]
                    extracted[key] = value

            fetch_results.append(
                FetchResult(
                    title=str(title)[:500],
                    content=str(content),
                    source_url=str(source_url),
                    published_at=(
                        self._safe_parse_date(str(date_str)) if date_str else None
                    ),
                    signal_type=signal_type,
                    extracted_data=extracted,
                    metadata={
                        "source_type": "api",
                        "provider": provider,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

        logger.info(
            f"API fetcher extracted {len(fetch_results)} results from {fallback_url}"
        )
        return fetch_results

    def _parse_ngx_market_response(
        self,
        data: Any,
        config: dict[str, Any],
        fallback_url: str,
    ) -> list[FetchResult]:
        """Parse NGX market data payloads into normalized fetch results."""
        signal_type = config.get("signal_type", "market")
        items = self._extract_ngx_items(data, config)
        results: list[FetchResult] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            symbol = self._first_value(
                item,
                "symbol",
                "ticker",
                "security",
                "security_name",
                "instrument",
                "name",
            )
            title = (
                self._first_value(item, "headline", "title", "name")
                or (f"{symbol} market update" if symbol else "NGX market update")
            )
            content = (
                self._first_value(item, "summary", "description", "commentary")
                or self._build_ngx_summary(item, symbol)
            )
            source_item_url = (
                self._first_value(item, "url", "source_url", "link") or fallback_url
            )
            published_at = self._safe_parse_date(
                str(
                    self._first_value(
                        item,
                        "timestamp",
                        "last_updated",
                        "as_of",
                        "trade_date",
                        "date",
                    )
                    or ""
                )
            )

            if not title and not content:
                continue

            extracted = {
                "symbol": symbol,
                "last_price": self._first_value(
                    item,
                    "last_price",
                    "last",
                    "price",
                    "close",
                    "value",
                ),
                "change": self._first_value(
                    item,
                    "change",
                    "price_change",
                    "change_value",
                    "net_change",
                ),
                "change_percent": self._first_value(
                    item,
                    "change_percent",
                    "percent_change",
                    "change_pct",
                ),
                "volume": self._first_value(
                    item,
                    "volume",
                    "trade_volume",
                    "traded_volume",
                    "total_volume",
                ),
            }

            results.append(
                FetchResult(
                    title=str(title)[:500],
                    content=str(content)[:10000],
                    source_url=str(source_item_url),
                    published_at=published_at,
                    signal_type=signal_type,
                    extracted_data={
                        key: value
                        for key, value in extracted.items()
                        if value not in (None, "")
                    },
                    metadata={
                        "source_type": "api",
                        "provider": "ngx_market_data",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

        logger.info(
            "API fetcher extracted %s NGX market records from %s",
            len(results),
            fallback_url,
        )
        return results

    def _extract_ngx_items(
        self,
        data: Any,
        config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        candidate_paths = [
            str(config.get("results_path", "")),
            "data.items",
            "data.results",
            "data.records",
            "data.prices",
            "data.history",
            "results",
            "items",
            "records",
            "prices",
            "history",
            "data",
        ]
        seen_paths: set[str] = set()

        for path in candidate_paths:
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            items = self._navigate_path(data, path)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
            if isinstance(items, dict):
                nested_list = next(
                    (
                        value
                        for value in items.values()
                        if isinstance(value, list)
                        and any(isinstance(entry, dict) for entry in value)
                    ),
                    None,
                )
                if nested_list:
                    return [item for item in nested_list if isinstance(item, dict)]

        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    @staticmethod
    def _first_value(item: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return None

    def _build_ngx_summary(self, item: dict[str, Any], symbol: Any) -> str:
        last_price = self._first_value(
            item,
            "last_price",
            "last",
            "price",
            "close",
            "value",
        )
        change = self._first_value(
            item,
            "change",
            "price_change",
            "change_value",
            "net_change",
        )
        change_percent = self._first_value(
            item,
            "change_percent",
            "percent_change",
            "change_pct",
        )
        volume = self._first_value(
            item,
            "volume",
            "trade_volume",
            "traded_volume",
            "total_volume",
        )

        parts = []
        if symbol:
            parts.append(f"{symbol} market snapshot")
        if last_price not in (None, ""):
            parts.append(f"last price {last_price}")
        if change not in (None, ""):
            parts.append(f"change {change}")
        if change_percent not in (None, ""):
            parts.append(f"({change_percent}%)")
        if volume not in (None, ""):
            parts.append(f"volume {volume}")
        return ". ".join(parts) if parts else "NGX market data update"

    @staticmethod
    def _navigate_path(data: Any, path: str) -> Any:
        """Navigate a dot-separated path in a dict/JSON structure.

        Example: _navigate_path(data, "articles.0.title")
        """
        if not path:
            return data

        parts = path.split(".")
        current = data

        for part in parts:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None

        return current
