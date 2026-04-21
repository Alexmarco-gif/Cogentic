"""Provider presets for signal acquisition contracts.

These helpers keep provider-specific wiring inside the existing fetcher model
instead of introducing separate job types or services.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.config import get_settings

DEFAULT_NEWSAPI_URL = "https://newsapi.org/v2/everything"
DEFAULT_X_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

_PROVIDER_SOURCE_TYPES = {
    "newsapi": "api",
    "ngx_market_data": "api",
    "x": "social",
    "linkedin_public": "scraper",
}


def normalize_provider_name(provider: str | None) -> str:
    """Normalize provider aliases to canonical preset names."""
    normalized = (provider or "generic").strip().lower()
    aliases = {
        "twitter": "x",
        "linkedin": "linkedin_public",
        "ngx": "ngx_market_data",
        "ngx_market_api": "ngx_market_data",
    }
    return aliases.get(normalized, normalized or "generic")


def infer_source_type_for_provider(provider: str | None) -> str | None:
    """Infer the fetcher type implied by a provider preset."""
    normalized = normalize_provider_name(provider)
    return _PROVIDER_SOURCE_TYPES.get(normalized)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def resolve_api_provider_config(
    source_url: str,
    extraction_config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Apply API-provider presets to a contract config."""
    config = deepcopy(extraction_config)
    provider = normalize_provider_name(config.get("provider"))
    settings = get_settings()

    if provider == "newsapi":
        api_key = (
            config.get("params", {}).get("apiKey")
            or config.get("auth", {}).get("api_key")
            or settings.newsapi_api_key
        )
        defaults = {
            "provider": "newsapi",
            "method": "GET",
            "params": {
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 25,
            },
            "results_path": "articles",
            "title_path": "title",
            "content_path": "description",
            "url_path": "url",
            "date_path": "publishedAt",
            "signal_type": "news",
            "extra_fields": ["author", "source.name"],
        }
        merged = _deep_merge(defaults, config)
        query = merged.get("params", {}).get("q") or merged.get("nl_query")
        if query:
            merged.setdefault("params", {})["q"] = query
        if api_key:
            merged.setdefault("params", {})["apiKey"] = api_key
        return source_url or DEFAULT_NEWSAPI_URL, merged

    if provider == "ngx_market_data":
        api_key = (
            config.get("auth", {}).get("api_key")
            or config.get("headers", {}).get("X-API-Key")
            or config.get("params", {}).get("api_key")
            or settings.ngx_market_data_api_key
        )
        auth_location = str(config.get("auth_location", "header")).lower()
        auth_header_name = config.get("auth_header_name", "X-API-Key")
        auth_param_name = config.get("auth_param_name", "api_key")
        defaults = {
            "provider": "ngx_market_data",
            "method": "GET",
            "signal_type": "market",
        }
        merged = _deep_merge(defaults, config)
        resolved_url = source_url or settings.ngx_market_data_base_url
        if api_key:
            if auth_location == "query":
                merged.setdefault("params", {})[auth_param_name] = api_key
            else:
                merged.setdefault("headers", {})[auth_header_name] = api_key
        return resolved_url, merged

    config["provider"] = provider
    return source_url, config


def resolve_social_provider_config(
    source_url: str,
    extraction_config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Apply social-provider presets to a contract config."""
    config = deepcopy(extraction_config)
    provider = normalize_provider_name(
        config.get("provider") or config.get("platform")
    )
    settings = get_settings()

    if provider == "x":
        bearer_token = (
            config.get("auth", {}).get("bearer_token") or settings.x_bearer_token
        )
        defaults = {
            "provider": "x",
            "platform": "x",
            "signal_type": "social",
            "params": {
                "max_results": 25,
                "tweet.fields": "created_at,public_metrics,author_id,lang",
            },
        }
        merged = _deep_merge(defaults, config)
        query = merged.get("params", {}).get("query") or merged.get("nl_query")
        if query:
            merged.setdefault("params", {})["query"] = query
        if bearer_token:
            merged.setdefault("auth", {})["bearer_token"] = bearer_token
        return source_url or DEFAULT_X_SEARCH_URL, merged

    config["provider"] = provider or "generic"
    return source_url, config


def resolve_scraper_provider_config(
    source_url: str,
    extraction_config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Apply scraper-provider presets to a contract config."""
    config = deepcopy(extraction_config)
    provider = normalize_provider_name(config.get("provider"))

    if provider == "linkedin_public":
        defaults = {
            "provider": "linkedin_public",
            "signal_type": "market",
            "item_selector": "html",
            "title_selector": "head > title",
            "content_selector": "main, body",
            "url_selector": "link[rel='canonical']",
            "url_attribute": "href",
            "headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            },
        }
        return source_url, _deep_merge(defaults, config)

    config["provider"] = provider
    return source_url, config


def apply_provider_contract_defaults(
    source_type: str,
    source_url: str,
    extraction_config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Resolve provider presets for any supported source type."""
    normalized_source_type = (source_type or "").strip().lower()

    if normalized_source_type == "api":
        return resolve_api_provider_config(source_url, extraction_config)
    if normalized_source_type == "social":
        return resolve_social_provider_config(source_url, extraction_config)
    if normalized_source_type == "scraper":
        return resolve_scraper_provider_config(source_url, extraction_config)
    return source_url, deepcopy(extraction_config)
