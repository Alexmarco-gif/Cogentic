import pytest

from backend.config import Settings, get_settings
from backend.signals.fetchers.api_fetcher import APIFetcher
from backend.signals.provider_presets import (
    resolve_api_provider_config,
    resolve_scraper_provider_config,
    resolve_social_provider_config,
)


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_newsapi_preset_uses_runtime_key_and_default_url(monkeypatch):
    monkeypatch.setenv("NEWSAPI_API_KEY", "news-key")

    source_url, config = resolve_api_provider_config(
        "",
        {
            "provider": "newsapi",
            "nl_query": "nigerian banking regulation",
        },
    )

    assert source_url == "https://newsapi.org/v2/everything"
    assert config["params"]["apiKey"] == "news-key"
    assert config["params"]["q"] == "nigerian banking regulation"
    assert config["results_path"] == "articles"
    assert config["signal_type"] == "news"


def test_ngx_market_data_preset_injects_runtime_auth_header(monkeypatch):
    monkeypatch.setenv("NGX_MARKET_DATA_API_KEY", "ngx-key")
    monkeypatch.setenv(
        "NGX_MARKET_DATA_BASE_URL",
        "https://ngxpulse.ng/api/ngxdata/market",
    )

    source_url, config = resolve_api_provider_config(
        "",
        {
            "provider": "ngx_market_data",
        },
    )

    assert source_url == "https://ngxpulse.ng/api/ngxdata/market"
    assert config["headers"]["X-API-Key"] == "ngx-key"
    assert config["signal_type"] == "market"


def test_x_social_preset_uses_runtime_bearer_and_default_endpoint(monkeypatch):
    monkeypatch.setenv("X_BEARER_TOKEN", "x-token")

    source_url, config = resolve_social_provider_config(
        "",
        {
            "provider": "x",
            "nl_query": "payments startup nigeria",
        },
    )

    assert source_url == "https://api.twitter.com/2/tweets/search/recent"
    assert config["auth"]["bearer_token"] == "x-token"
    assert config["params"]["query"] == "payments startup nigeria"
    assert config["platform"] == "x"


def test_linkedin_public_scraper_preset_applies_selectors():
    source_url, config = resolve_scraper_provider_config(
        "https://www.linkedin.com/company/example/",
        {
            "provider": "linkedin_public",
        },
    )

    assert source_url == "https://www.linkedin.com/company/example/"
    assert config["item_selector"] == "html"
    assert config["title_selector"] == "head > title"
    assert config["content_selector"] == "main, body"
    assert config["headers"]["Accept-Language"] == "en-US,en;q=0.9"


def test_api_fetcher_parses_ngx_market_payload_into_signal_results():
    fetcher = APIFetcher()

    results = fetcher._parse_response(
        {
            "data": {
                "prices": [
                    {
                        "symbol": "ACCESSCORP",
                        "last_price": 21.4,
                        "change": 0.5,
                        "change_percent": 2.39,
                        "volume": 102300,
                        "trade_date": "2026-03-27",
                    }
                ]
            }
        },
        {
            "provider": "ngx_market_data",
            "signal_type": "market",
        },
        "https://ngxpulse.ng/api/ngxdata/market",
    )

    assert len(results) == 1
    assert results[0].signal_type == "market"
    assert results[0].extracted_data["symbol"] == "ACCESSCORP"
    assert results[0].metadata["provider"] == "ngx_market_data"
    assert "last price 21.4" in results[0].content


def test_production_settings_require_provider_credentials():
    with pytest.raises(ValueError, match="NEWSAPI_API_KEY"):
        Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/cogent",
            auth0_domain="example.auth0.com",
            auth0_audience="https://api.cogent.test",
            auth0_m2m_client_id="client-id",
            auth0_m2m_client_secret="client-secret",
            secret_key="development-secret-key-with-enough-length",
            environment="production",
            debug=False,
            openai_api_key="openai-key",
            neo4j_uri="bolt://localhost:7687",
        )
