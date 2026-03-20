"""Helpers for localizing live web-search requests."""

import json
import logging
from functools import lru_cache
from pathlib import Path

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

ISO_3166_1_JSON_PATH = Path("/usr/share/iso-codes/json/iso_3166-1.json")


@lru_cache
def _load_alpha3_to_alpha2_map() -> dict[str, str]:
    """Load the complete ISO 3166-1 alpha-3 → alpha-2 mapping from iso-codes."""
    try:
        with ISO_3166_1_JSON_PATH.open(encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError:
        logger.warning("ISO country source not found at %s", ISO_3166_1_JSON_PATH)
        return {}
    except Exception as exc:
        logger.warning(
            "Failed to load ISO country source from %s: %s",
            ISO_3166_1_JSON_PATH,
            exc,
        )
        return {}

    countries = payload.get("3166-1", [])
    mapping: dict[str, str] = {}
    for country in countries:
        alpha2 = (country.get("alpha_2") or "").strip().lower()
        alpha3 = (country.get("alpha_3") or "").strip().upper()
        if alpha2 and alpha3:
            mapping[alpha3] = alpha2

    return mapping


def normalize_search_country(country: str | None) -> str | None:
    """Normalize tenant country codes to the alpha-2 form expected by SerpApi."""
    value = (country or "").strip()
    if not value:
        return None

    if len(value) == 2 and value.isalpha():
        return value.lower()

    if len(value) == 3 and value.isalpha():
        return _load_alpha3_to_alpha2_map().get(value.upper())

    return None


def normalize_search_language(language: str | None) -> str:
    """Normalize tenant locale strings to a search-language code."""
    value = (language or "").strip()
    if not value:
        return settings.web_search_default_language or "en"

    primary = value.split("-", 1)[0].split("_", 1)[0].strip().lower()
    return primary or settings.web_search_default_language or "en"


def resolve_search_locale(
    *,
    country: str | None = None,
    language: str | None = None,
) -> tuple[str | None, str]:
    """Resolve normalized country/language with config defaults."""
    normalized_country = normalize_search_country(country)
    if normalized_country is None:
        normalized_country = normalize_search_country(
            settings.web_search_default_country
        )

    return normalized_country, normalize_search_language(language)
