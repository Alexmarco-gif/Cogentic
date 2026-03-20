"""Helpers for localizing live web-search requests."""

from backend.config import get_settings

settings = get_settings()

# Minimal ISO 3166-1 alpha-3 → alpha-2 map for current tenant regions plus
# common fallback markets. Extend as new regions are added.
_ALPHA3_TO_ALPHA2 = {
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
    "KEN": "ke",
    "MAR": "ma",
    "NGA": "ng",
    "TZA": "tz",
    "UGA": "ug",
    "USA": "us",
    "ZAF": "za",
}


def normalize_search_country(country: str | None) -> str | None:
    """Normalize tenant country codes to the alpha-2 form expected by SerpApi."""
    value = (country or "").strip()
    if not value:
        return None

    if len(value) == 2 and value.isalpha():
        return value.lower()

    if len(value) == 3 and value.isalpha():
        return _ALPHA3_TO_ALPHA2.get(value.upper())

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
