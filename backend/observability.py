"""Observability configuration for logging, metrics, and tracing"""

import logging
import structlog
from prometheus_client import Counter, Histogram

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Prometheus metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)


def get_logger(name: str):
    """Get a structured logger instance"""
    return structlog.get_logger(name)


def init_observability(
    environment: str,
    version: str,
    sentry_dsn: str | None = None,
    logtail_token: str | None = None,
    posthog_api_key: str | None = None,
):
    """
    Initialize observability tools (Sentry, logging, PostHog)

    Args:
        environment: Current environment (development, staging, production)
        version: Application version
        sentry_dsn: Sentry DSN for error tracking (optional)
        logtail_token: Logtail token for log aggregation (optional)
        posthog_api_key: PostHog API key for product analytics (optional)
    """
    # Configure logging level based on environment
    log_level = logging.DEBUG if environment == "development" else logging.INFO
    logging.basicConfig(level=log_level)

    logger = get_logger(__name__)
    logger.info(
        "observability_initialized",
        environment=environment,
        version=version,
        sentry_enabled=bool(sentry_dsn),
        logtail_enabled=bool(logtail_token),
        posthog_enabled=bool(posthog_api_key),
    )

    # Initialize Sentry if DSN provided
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=environment,
                release=version,
                traces_sample_rate=0.1,  # 10% of transactions
                integrations=[FastApiIntegration()],
            )
            logger.info("sentry_initialized")
        except ImportError:
            logger.warning("sentry_sdk_not_installed")
        except Exception as e:
            logger.error("sentry_initialization_failed", error=str(e))

    # Initialize PostHog if API key provided
    if posthog_api_key:
        try:
            import posthog

            posthog.api_key = posthog_api_key
            posthog.host = "https://app.posthog.com"
            logger.info("posthog_initialized")
        except ImportError:
            logger.warning("posthog_not_installed")
        except Exception as e:
            logger.error("posthog_initialization_failed", error=str(e))

    logger.info(
        "observability_ready",
        environment=environment,
        version=version,
    )
