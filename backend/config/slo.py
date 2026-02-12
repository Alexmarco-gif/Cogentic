"""SLO (Service Level Objective) configuration.

Defines performance targets for key operations:
  - API response times (p50, p95, p99)
  - Background job durations
  - Cache hit rates
  - AI call success rates
  - Data freshness

Monitored via Grafana dashboards.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class SLOTarget:
    """SLO target definition."""

    name: str
    description: str
    p50_ms: int | None = None
    p95_ms: int | None = None
    p99_ms: int | None = None
    success_rate_pct: float | None = None
    availability_pct: float | None = None
    metric_query: str | None = None  # PromQL or equivalent


class SLOConfig:
    """SLO configuration for ESIP platform."""

    # API Response Times
    API_SEARCH = SLOTarget(
        name="api.search.latency",
        description="Deep Live Search API response time",
        p50_ms=1500,
        p95_ms=5000,
        p99_ms=8000,
        metric_query='histogram_quantile(0.95, search_duration_seconds_bucket)',
    )

    API_SYNTHESIS = SLOTarget(
        name="api.synthesis.latency",
        description="RAG Synthesis API response time",
        p50_ms=2000,
        p95_ms=6000,
        p99_ms=10000,
        metric_query='histogram_quantile(0.95, synthesis_duration_seconds_buffer)',
    )

    API_BRIEF_GENERATION = SLOTarget(
        name="api.brief_generation.latency",
        description="Intelligence Brief generation time",
        p50_ms=8000,
        p95_ms=15000,
        p99_ms=25000,
        metric_query='histogram_quantile(0.95, brief_generation_duration_seconds_bucket)',
    )

    API_RECOMMENDATIONS = SLOTarget(
        name="api.recommendations.latency",
        description="Recommendation retrieval time",
        p50_ms=200,
        p95_ms=500,
        p99_ms=1000,
        metric_query='histogram_quantile(0.95, recommendations_duration_seconds_bucket)',
    )

    # Background Jobs
    JOB_SIGNAL_ACQUISITION = SLOTarget(
        name="job.signal_acquisition.duration",
        description="Signal acquisition per contract",
        p50_ms=5000,
        p95_ms=15000,
        p99_ms=30000,
    )

    JOB_REFINEMENT = SLOTarget(
        name="job.refinement.duration",
        description="Signal refinement per batch (100 signals)",
        p50_ms=15000,
        p95_ms=45000,
        p99_ms=90000,
    )

    JOB_BRIEF_REFRESH = SLOTarget(
        name="job.brief_refresh.duration",
        description="Brief auto-refresh check (all briefs)",
        p50_ms=10000,
        p95_ms=30000,
        p99_ms=60000,
    )

    # Success Rates
    AI_COMPLETION_SUCCESS = SLOTarget(
        name="ai.completion.success_rate",
        description="OpenAI completion success rate (excludes 429s)",
        success_rate_pct=99.5,
        metric_query='sum(rate(ai_completion_success_total[5m])) / sum(rate(ai_completion_attempts_total[5m]))',
    )

    SIGNAL_ACQUISITION_SUCCESS = SLOTarget(
        name="signal.acquisition.success_rate",
        description="Signal acquisition success rate per contract",
        success_rate_pct=95.0,
        metric_query='sum(rate(signal_acquisition_success_total[1h])) / sum(rate(signal_acquisition_attempts_total[1h]))',
    )

    # Cache Performance
    SEARCH_CACHE_HIT_RATE = SLOTarget(
        name="cache.search.hit_rate",
        description="Search result cache hit rate",
        success_rate_pct=40.0,  # Target 40% hit rate
        metric_query='sum(rate(search_cache_hits_total[5m])) / sum(rate(search_requests_total[5m]))',
    )

    SYNTHESIS_CACHE_HIT_RATE = SLOTarget(
        name="cache.synthesis.hit_rate",
        description="Synthesis cache hit rate",
        success_rate_pct=35.0,  # Target 35% hit rate
        metric_query='sum(rate(synthesis_cache_hits_total[5m])) / sum(rate(synthesis_requests_total[5m]))',
    )

    # Data Freshness
    SIGNAL_FRESHNESS = SLOTarget(
        name="data.signal.freshness",
        description="Time since last signal refresh per contract",
        p95_ms=3600000,  # 1 hour
        p99_ms=7200000,  # 2 hours
        metric_query='histogram_quantile(0.95, signal_age_seconds_bucket)',
    )

    # Availability
    API_AVAILABILITY = SLOTarget(
        name="api.availability",
        description="Overall API availability (non-5xx)",
        availability_pct=99.9,
        metric_query='sum(rate(http_requests_total{status!~"5.."}[5m])) / sum(rate(http_requests_total[5m]))',
    )

    @classmethod
    def get_all_targets(cls) -> dict[str, SLOTarget]:
        """Get all SLO targets as a dict."""
        return {
            attr: getattr(cls, attr)
            for attr in dir(cls)
            if isinstance(getattr(cls, attr), SLOTarget)
        }

    @classmethod
    def to_dashboard_config(cls) -> list[dict[str, Any]]:
        """Export SLO targets as Grafana dashboard config."""
        targets = cls.get_all_targets()
        panels = []

        for key, target in targets.items():
            panel = {
                "title": target.name,
                "description": target.description,
                "type": "graph",
                "targets": [],
            }

            if target.metric_query:
                panel["targets"].append({
                    "expr": target.metric_query,
                    "legendFormat": "Current",
                })

            if target.p95_ms:
                panel["thresholds"] = [{
                    "value": target.p95_ms,
                    "colorMode": "critical",
                    "op": "gt",
                    "fill": True,
                    "line": True,
                }]

            panels.append(panel)

        return panels
