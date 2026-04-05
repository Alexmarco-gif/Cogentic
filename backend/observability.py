"""Observability configuration for logging, metrics, and tracing.

Centralises structured logging (structlog), Prometheus metric declarations,
Sentry error tracking, Logtail log aggregation, PostHog product analytics,
and OpenTelemetry distributed tracing configuration.
"""

import logging

import structlog
from prometheus_client import Counter, Gauge, Histogram, Info

# ── Structured Logging ───────────────────────────────────────────────

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

# ── Prometheus Metrics ───────────────────────────────────────────────
# HTTP
http_requests_total = Counter(
    "cogent_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "cogent_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# Database pool
db_pool_checked_out = Gauge(
    "cogent_db_pool_checked_out",
    "Number of database connections currently checked out from the pool",
    ["engine"],
)

db_pool_overflow = Gauge(
    "cogent_db_pool_overflow",
    "Current overflow connection count above pool_size",
    ["engine"],
)

db_pool_size = Gauge(
    "cogent_db_pool_size",
    "Configured pool size for the database engine",
    ["engine"],
)

db_query_total = Counter(
    "cogent_db_query_total",
    "Total database queries executed",
)

db_slow_query_total = Counter(
    "cogent_db_slow_query_total",
    "Total slow database queries (>100ms)",
)

db_query_duration_seconds = Histogram(
    "cogent_db_query_duration_seconds",
    "Database query duration in seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Redis
redis_connected_clients = Gauge(
    "cogent_redis_connected_clients",
    "Number of connected Redis clients",
)

redis_used_memory_bytes = Gauge(
    "cogent_redis_used_memory_bytes",
    "Total memory used by Redis in bytes",
)

redis_total_keys = Gauge(
    "cogent_redis_total_keys",
    "Total number of keys across all Redis databases",
)

redis_pool_active = Gauge(
    "cogent_redis_pool_active",
    "Active connections in the Redis connection pool",
)

# Job queue (RQ)
job_queue_pending = Gauge(
    "cogent_job_queue_pending",
    "Number of pending jobs in the RQ queue",
    ["queue"],
)

job_queue_failed = Gauge(
    "cogent_job_queue_failed",
    "Number of failed jobs in the RQ queue",
    ["queue"],
)

job_queue_scheduled = Gauge(
    "cogent_job_queue_scheduled",
    "Number of scheduled jobs in the RQ queue",
    ["queue"],
)

# AI cost tracking
ai_tokens_total = Counter(
    "cogent_ai_tokens_total",
    "Total AI tokens consumed",
    ["model", "type"],  # type = prompt | completion
)

ai_cost_usd_total = Counter(
    "cogent_ai_cost_usd_total",
    "Total estimated AI cost in USD",
    ["model"],
)

ai_budget_usage_ratio = Gauge(
    "cogent_ai_budget_usage_ratio",
    "Current AI budget usage ratio (0.0–1.0+). >1.0 means over-budget.",
    ["scope"],  # user | org
)

ai_budget_exceeded_total = Counter(
    "cogent_ai_budget_exceeded_total",
    "Number of times an AI budget was exceeded",
    ["scope"],
)

# WebSocket
ws_connections_active = Gauge(
    "cogent_ws_connections_active",
    "Number of active WebSocket connections",
)

ws_rooms_active = Gauge(
    "cogent_ws_rooms_active",
    "Number of active WebSocket rooms (industries)",
)

ws_messages_sent_total = Counter(
    "cogent_ws_messages_sent_total",
    "Total WebSocket messages broadcast to clients",
)

# App info
app_info = Info(
    "cogent_app",
    "Application build information",
)


def get_logger(name: str):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# ── Metrics Collection Callbacks ─────────────────────────────────────


def collect_db_pool_metrics(primary_engine, replica_engine=None):
    """Snapshot SQLAlchemy pool stats into Prometheus Gauges.

    Called periodically or on /metrics scrape.
    """
    for label, eng in [("primary", primary_engine), ("read", replica_engine)]:
        if eng is None:
            continue
        pool = eng.pool
        db_pool_size.labels(engine=label).set(pool.size())
        db_pool_checked_out.labels(engine=label).set(pool.checkedout())
        db_pool_overflow.labels(engine=label).set(pool.overflow())


async def collect_redis_metrics(redis_client):
    """Snapshot Redis server INFO stats into Prometheus Gauges."""
    try:
        info = await redis_client.info(section="all")
        redis_connected_clients.set(info.get("connected_clients", 0))
        redis_used_memory_bytes.set(info.get("used_memory", 0))

        # Sum keys across all databases
        total_keys = 0
        for key, val in info.items():
            if key.startswith("db") and isinstance(val, dict):
                total_keys += val.get("keys", 0)
        redis_total_keys.set(total_keys)

        # Connection pool info (if available)
        pool = redis_client.connection_pool
        if hasattr(pool, "_created_connections"):
            redis_pool_active.set(pool._created_connections)
        elif hasattr(pool, "_in_use_connections"):
            redis_pool_active.set(len(pool._in_use_connections))
    except Exception:
        pass  # Don't crash metrics collection


def collect_job_queue_metrics():
    """Snapshot RQ queue depths into Prometheus Gauges.

    Uses lazy import to avoid circular dependency with job_queue module.
    """
    try:
        from backend.job_queue import (
            get_default_queue,
            get_high_priority_queue,
            get_low_priority_queue,
        )

        for name, getter in [
            ("high", get_high_priority_queue),
            ("default", get_default_queue),
            ("low", get_low_priority_queue),
        ]:
            q = getter()
            job_queue_pending.labels(queue=name).set(len(q))
            job_queue_failed.labels(queue=name).set(q.failed_job_registry.count)
            job_queue_scheduled.labels(queue=name).set(q.scheduled_job_registry.count)
    except Exception:
        pass  # Redis may be unavailable


# ── Initialisation ───────────────────────────────────────────────────


def init_observability(
    environment: str,
    version: str,
    sentry_dsn: str | None = None,
    logtail_token: str | None = None,
    posthog_api_key: str | None = None,
    posthog_host: str | None = None,
):
    """Initialise observability stack (Sentry, Logtail, PostHog, OpenTelemetry).

    Args:
        environment: Current environment (development, staging, production)
        version: Application version
        sentry_dsn: Sentry DSN for error tracking (optional)
        logtail_token: Logtail/Better Stack source token (optional)
        posthog_api_key: PostHog API key for product analytics (optional)
        posthog_host: PostHog ingestion host (optional)
    """
    # Configure logging level based on environment
    log_level = logging.DEBUG if environment == "development" else logging.INFO
    logging.basicConfig(level=log_level)

    logger = get_logger(__name__)

    # Set build info metric
    app_info.info(
        {
            "version": version,
            "environment": environment,
        }
    )

    logger.info(
        "observability_initialized",
        environment=environment,
        version=version,
        sentry_enabled=bool(sentry_dsn),
        logtail_enabled=bool(logtail_token),
        posthog_enabled=bool(posthog_api_key),
    )

    # ── Sentry ────────────────────────────────────────────────────
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=environment,
                release=version,
                traces_sample_rate=0.1,  # 10% of transactions
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                ],
            )
            logger.info("sentry_initialized")
        except ImportError:
            logger.warning("sentry_sdk_not_installed")
        except Exception as e:
            logger.error("sentry_initialization_failed", error=str(e))

    # ── Logtail / Better Stack ────────────────────────────────────
    if logtail_token:
        try:
            from logtail import LogtailHandler

            handler = LogtailHandler(source_token=logtail_token)
            handler.setLevel(log_level)
            # Attach to root logger so structlog-emitted records are forwarded
            logging.getLogger().addHandler(handler)
            logger.info("logtail_initialized")
        except ImportError:
            logger.warning(
                "logtail_not_installed",
                hint="pip install logtail-python",
            )
        except Exception as e:
            logger.error("logtail_initialization_failed", error=str(e))

    # ── PostHog ───────────────────────────────────────────────────
    if posthog_api_key:
        try:
            import posthog

            posthog.api_key = posthog_api_key
            posthog.host = posthog_host or "https://app.posthog.com"
            logger.info("posthog_initialized", host=posthog.host)
        except ImportError:
            logger.warning("posthog_not_installed")
        except Exception as e:
            logger.error("posthog_initialization_failed", error=str(e))

    # ── OpenTelemetry Distributed Tracing ─────────────────────────
    _init_opentelemetry(environment, version, logger)

    logger.info(
        "observability_ready",
        environment=environment,
        version=version,
    )


def _init_opentelemetry(environment: str, version: str, logger):
    """Configure OpenTelemetry OTLP exporter if OTEL_EXPORTER_OTLP_ENDPOINT is set."""
    import os

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {
                "service.name": "cogent-backend",
                "service.version": version,
                "deployment.environment": environment,
            }
        )

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        logger.info("opentelemetry_initialized", endpoint=otlp_endpoint)
    except ImportError:
        logger.warning(
            "opentelemetry_not_fully_installed",
            hint="pip install opentelemetry-sdk opentelemetry-exporter-otlp",
        )
    except Exception as e:
        logger.error("opentelemetry_initialization_failed", error=str(e))
