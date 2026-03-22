"""Helpers for localizing live web-search requests."""

import json
import logging
from functools import lru_cache
from pathlib import Path

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

ISO_3166_1_JSON_PATH = Path("/usr/share/iso-codes/json/iso_3166-1.json")

# Common markets kept locally so locale normalization still works when the
# optional iso-codes package is unavailable in a given runtime image.
_FALLBACK_ALPHA3_TO_ALPHA2 = {
    "AUS": "au",
    "CAN": "ca",
    "CIV": "ci",
    "DEU": "de",
    "ETH": "et",
    "FRA": "fr",
    "GBR": "gb",
    "GHA": "gh",
    "IND": "in",
    "IRL": "ie",
    "JPN": "jp",
    "KEN": "ke",
    "MAR": "ma",
    "NGA": "ng",
    "TZA": "tz",
    "UGA": "ug",
    "USA": "us",
    "ZAF": "za",
}


@lru_cache
def _load_alpha3_to_alpha2_map() -> dict[str, str]:
    """Load alpha-3 to alpha-2 mappings with a resilient local fallback."""
    mapping = dict(_FALLBACK_ALPHA3_TO_ALPHA2)

    try:
        with ISO_3166_1_JSON_PATH.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        logger.warning("ISO country source not found at %s", ISO_3166_1_JSON_PATH)
        return mapping
    except Exception as exc:
        logger.warning(
            "Failed to load ISO country source from %s: %s",
            ISO_3166_1_JSON_PATH,
            exc,
        )
        return mapping

    for country in payload.get("3166-1", []):
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
