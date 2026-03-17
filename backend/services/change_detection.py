"""Change detection service — anomaly detection for MarketDataPoint values.

Compares newly persisted market data points against a rolling 30-day
baseline (mean ± stddev) and creates SignalAlert rows when values
deviate significantly.

Z-score thresholds:
  |z| >= 3.0 → critical
  |z| >= 2.5 → high
  |z| >= 2.0 → medium
  |z| >= 1.5 → low  (only if min_history_points >= 5)
"""

import logging
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.market_data import MarketDataPoint
from backend.models.signal_alert import SignalAlert

logger = logging.getLogger(__name__)

# Minimum historical data points required before alerting
MIN_HISTORY_POINTS = 5
# Rolling window in days for baseline calculation
BASELINE_WINDOW_DAYS = 30

# Z-score → severity mapping
_SEVERITY_THRESHOLDS = [
    (3.0, "critical"),
    (2.5, "high"),
    (2.0, "medium"),
    (1.5, "low"),
]


class ChangeDetectionService:
    """Detects anomalous changes in market metric values.

    Computes a rolling mean and standard deviation for the last
    BASELINE_WINDOW_DAYS days of a given (metric, country_code) pair,
    then calculates the z-score of the new data point.

    A SignalAlert is created when the z-score exceeds 1.5 and
    there are at least MIN_HISTORY_POINTS historical observations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect(self, market_data_point: MarketDataPoint) -> SignalAlert | None:
        """Run change detection on a newly persisted MarketDataPoint.

        Args:
            market_data_point: The freshly created data point to evaluate.

        Returns:
            A persisted SignalAlert if an anomaly is detected, else None.
        """
        metric = market_data_point.metric
        country_code = market_data_point.country_code
        new_value = market_data_point.value

        # Fetch historical baseline (exclude the current point)
        baseline_stats = await self._get_baseline_stats(
            metric=metric,
            country_code=country_code,
            exclude_id=market_data_point.id,
        )

        count = baseline_stats["count"]
        if count < MIN_HISTORY_POINTS:
            return None  # Not enough history to make a meaningful judgment

        mean = baseline_stats["mean"]
        stddev = baseline_stats["stddev"]

        if stddev is None or stddev < 1e-9:
            return None  # No variance — all historical values identical

        z_score = abs(new_value - mean) / stddev
        severity = self._classify_severity(z_score)
        if severity is None:
            return None  # Within normal range

        deviation_pct = ((new_value - mean) / abs(mean) * 100) if mean != 0 else 0.0
        direction = "above" if new_value > mean else "below"
        unit_hint = f" {market_data_point.unit}" if market_data_point.unit else ""

        title = (
            f"Anomalous {metric} value: {new_value:.2f}{unit_hint} "
            f"({direction} baseline by {abs(deviation_pct):.1f}%)"
        )
        description = (
            f"The metric '{metric}' recorded a value of {new_value:.4f}{unit_hint}, "
            f"which is {abs(deviation_pct):.1f}% {direction} the 30-day baseline "
            f"of {mean:.4f}{unit_hint} (z-score={z_score:.2f}, n={count})."
        )
        if country_code:
            description += f" Country: {country_code}."

        alert = SignalAlert(
            id=uuid4(),
            signal_id=market_data_point.signal_id,
            entity_id=market_data_point.entity_id,
            alert_type="anomaly",
            severity=severity,
            metric=metric,
            country_code=country_code,
            title=title,
            description=description,
            current_value=new_value,
            baseline_value=round(mean, 6),
            deviation_pct=round(deviation_pct, 2),
        )

        self.db.add(alert)
        await self.db.flush()

        logger.info(
            "Signal alert created: metric=%s severity=%s z=%.2f country=%s",
            metric,
            severity,
            z_score,
            country_code,
        )
        return alert

    async def _get_baseline_stats(
        self,
        *,
        metric: str,
        country_code: str | None,
        exclude_id: UUID,
    ) -> dict:
        """Compute mean, stddev, count for historical data points.

        Uses two queries (count+mean, then variance) so that the implementation
        is portable across both PostgreSQL (production) and SQLite (tests)
        without relying on ``func.stddev_pop``.
        """
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=BASELINE_WINDOW_DAYS)

        filters = [
            MarketDataPoint.metric == metric,
            MarketDataPoint.observed_at >= cutoff,
            MarketDataPoint.id != exclude_id,
        ]
        if country_code:
            filters.append(MarketDataPoint.country_code == country_code)

        # First pass: count + mean (works everywhere)
        result = await self.db.execute(
            select(
                func.count(MarketDataPoint.id).label("count"),
                func.avg(MarketDataPoint.value).label("mean"),
            ).where(*filters)
        )
        row = result.one()
        count = row.count or 0
        mean = float(row.mean) if row.mean is not None else 0.0

        if count < MIN_HISTORY_POINTS:
            return {"count": count, "mean": mean, "stddev": None}

        # Second pass: E[(x - mean)^2] = population variance (works everywhere)
        result2 = await self.db.execute(
            select(
                func.avg(
                    (MarketDataPoint.value - mean) * (MarketDataPoint.value - mean)
                ).label("variance")
            ).where(*filters)
        )
        row2 = result2.one()
        variance = float(row2.variance) if row2.variance is not None else 0.0
        stddev = variance**0.5  # Python sqrt — no SQL sqrt needed

        return {"count": count, "mean": mean, "stddev": stddev}

    @staticmethod
    def _classify_severity(z_score: float) -> str | None:
        """Map z-score to severity string or None if within normal range."""
        for threshold, severity in _SEVERITY_THRESHOLDS:
            if z_score >= threshold:
                return severity
        return None
