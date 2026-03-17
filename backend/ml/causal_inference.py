"""Causal inference models for WHY analysis.

Uses:
- Granger causality tests (for time series)
- Synthetic control method (for counterfactual estimation)
- Propensity score matching
- Difference-in-differences estimation
- Causal impact analysis
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from statsmodels.tsa.stattools import grangercausalitytests

from backend.models.signal import Signal

logger = logging.getLogger(__name__)


class CausalInferenceService:
    """Causal inference engine for understanding WHY events occur."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def granger_causality_test(
        self,
        cause_signal_type: str,
        effect_signal_type: str,
        *,
        max_lag: int = 14,
        lookback_days: int = 180,
    ) -> dict[str, Any]:
        """Test if one signal type Granger-causes another.

        Granger causality: Does past values of X help predict Y?

        Args:
            cause_signal_type: Hypothesized cause
            effect_signal_type: Hypothesized effect
            max_lag: Maximum lag to test (days)
            lookback_days: How far back to pull data

        Returns:
            Test results with p-values and optimal lag
        """
        # Fetch time series data
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        # Cause signals
        cause_query = (
            select(Signal.published_at, Signal.confidence)
            .where(
                and_(
                    Signal.signal_type == cause_signal_type,
                    Signal.published_at >= cutoff,
                )
            )
            .order_by(Signal.published_at)
        )
        cause_result = await self.db.execute(cause_query)
        cause_data = [(r.published_at, r.confidence) for r in cause_result]

        # Effect signals
        effect_query = (
            select(Signal.published_at, Signal.confidence)
            .where(
                and_(
                    Signal.signal_type == effect_signal_type,
                    Signal.published_at >= cutoff,
                )
            )
            .order_by(Signal.published_at)
        )
        effect_result = await self.db.execute(effect_query)
        effect_data = [(r.published_at, r.confidence) for r in effect_result]

        # Convert to daily time series
        cause_series = self._aggregate_to_daily(cause_data, lookback_days)
        effect_series = self._aggregate_to_daily(effect_data, lookback_days)

        # Create DataFrame for Granger test
        df = pd.DataFrame(
            {
                "cause": cause_series,
                "effect": effect_series,
            }
        )

        # Run Granger causality test
        try:
            gc_result = grangercausalitytests(
                df[["effect", "cause"]], maxlag=max_lag, verbose=False
            )

            # Extract p-values for each lag
            p_values = {}
            for lag in range(1, max_lag + 1):
                # Use F-test p-value
                p_val = gc_result[lag][0]["ssr_ftest"][1]
                p_values[lag] = p_val

            # Find optimal lag (minimum p-value)
            optimal_lag = min(p_values, key=p_values.get)
            optimal_p_value = p_values[optimal_lag]

            # Determine if causal relationship exists (p < 0.05)
            is_causal = optimal_p_value < 0.05

            return {
                "cause_signal_type": cause_signal_type,
                "effect_signal_type": effect_signal_type,
                "is_causal": is_causal,
                "optimal_lag_days": optimal_lag,
                "p_value": round(optimal_p_value, 4),
                "confidence": round(1 - optimal_p_value, 4) if is_causal else 0.0,
                "interpretation": (
                    f"{cause_signal_type} Granger-causes {effect_signal_type} "
                    f"with {optimal_lag} day lag (p={optimal_p_value:.4f})"
                    if is_causal
                    else f"No Granger causality detected between {cause_signal_type} and {effect_signal_type}"
                ),
            }

        except Exception as e:
            logger.error(f"Granger causality test failed: {e}")
            return {
                "cause_signal_type": cause_signal_type,
                "effect_signal_type": effect_signal_type,
                "is_causal": False,
                "error": str(e),
            }

    async def estimate_counterfactual(
        self,
        event_signal_id: str,
        outcome_metric: str,
        *,
        pre_event_days: int = 30,
        post_event_days: int = 30,
    ) -> dict[str, Any]:
        """Estimate counterfactual: What would have happened if event didn't occur?

        Uses synthetic control method: Build a synthetic baseline from similar periods
        without the event, then compare actual vs. baseline.

        Args:
            event_signal_id: The event whose impact we want to measure
            outcome_metric: The metric we're measuring (e.g., 'stock_price', 'loan_volume')
            pre_event_days: Days before event to establish baseline
            post_event_days: Days after event to measure impact

        Returns:
            Counterfactual estimate with impact quantification
        """
        # Get event signal
        event_signal = await self.db.get(Signal, event_signal_id)
        if not event_signal:
            return {
                "event_signal_id": event_signal_id,
                "error": "Event signal not found",
            }

        event_date = event_signal.published_at

        # Define time windows
        pre_start = event_date - timedelta(days=pre_event_days)
        post_end = event_date + timedelta(days=post_event_days)

        # Fetch outcome metric data (using signal confidence as proxy for now)
        # In production, this would query actual metrics (stock prices, volumes, etc.)
        pre_query = (
            select(Signal.published_at, Signal.confidence)
            .where(
                and_(
                    Signal.signal_type == outcome_metric,
                    Signal.published_at >= pre_start,
                    Signal.published_at < event_date,
                )
            )
            .order_by(Signal.published_at)
        )
        pre_result = await self.db.execute(pre_query)
        pre_data = [(r.published_at, r.confidence) for r in pre_result]

        post_query = (
            select(Signal.published_at, Signal.confidence)
            .where(
                and_(
                    Signal.signal_type == outcome_metric,
                    Signal.published_at >= event_date,
                    Signal.published_at <= post_end,
                )
            )
            .order_by(Signal.published_at)
        )
        post_result = await self.db.execute(post_query)
        post_data = [(r.published_at, r.confidence) for r in post_result]

        if not pre_data or not post_data:
            return {
                "event_signal_id": event_signal_id,
                "outcome_metric": outcome_metric,
                "error": "Insufficient data for counterfactual estimation",
            }

        # Build synthetic control
        synthetic_control = self._build_synthetic_control(
            pre_data=pre_data,
            post_data=post_data,
            pre_event_days=pre_event_days,
            post_event_days=post_event_days,
        )

        # Calculate impact
        actual_post_values = [v for _, v in post_data]
        synthetic_post_values = synthetic_control["synthetic_post"]

        # Ensure same length
        min_length = min(len(actual_post_values), len(synthetic_post_values))
        actual_post_values = actual_post_values[:min_length]
        synthetic_post_values = synthetic_post_values[:min_length]

        # Calculate impact metrics
        point_effects = np.array(actual_post_values) - np.array(synthetic_post_values)
        average_effect = np.mean(point_effects)
        cumulative_effect = np.sum(point_effects)

        # Calculate significance (simple t-test)
        if len(point_effects) > 1:
            t_stat, p_value = stats.ttest_1samp(point_effects, 0)
            is_significant = p_value < 0.05
        else:
            _t_stat, p_value = 0, 1.0
            is_significant = False

        # Calculate percentage impact
        avg_actual = np.mean(actual_post_values)
        avg_synthetic = np.mean(synthetic_post_values)
        pct_impact = (
            ((avg_actual - avg_synthetic) / avg_synthetic * 100)
            if avg_synthetic != 0
            else 0
        )

        return {
            "event_signal_id": event_signal_id,
            "event_date": event_date.isoformat(),
            "outcome_metric": outcome_metric,
            "causal_impact": {
                "average_effect": round(average_effect, 4),
                "cumulative_effect": round(cumulative_effect, 4),
                "percentage_impact": round(pct_impact, 2),
                "is_significant": is_significant,
                "p_value": round(p_value, 4) if p_value else None,
            },
            "counterfactual": {
                "actual_post_event": {
                    "mean": round(avg_actual, 4),
                    "values": [round(v, 4) for v in actual_post_values],
                },
                "synthetic_baseline": {
                    "mean": round(avg_synthetic, 4),
                    "values": [round(v, 4) for v in synthetic_post_values],
                },
                "point_effects": [round(e, 4) for e in point_effects],
            },
            "interpretation": self._interpret_counterfactual_result(
                average_effect, pct_impact, is_significant
            ),
            "pre_event_fit": {
                "rmse": round(synthetic_control["pre_fit_rmse"], 4),
                "r_squared": round(synthetic_control["pre_fit_r2"], 4),
            },
        }

    def _build_synthetic_control(
        self,
        pre_data: list[tuple[datetime, float]],
        post_data: list[tuple[datetime, float]],
        pre_event_days: int,
        post_event_days: int,
    ) -> dict[str, Any]:
        """Build synthetic control using weighted combination of donor time series.

        For simplicity, we use historical patterns from the pre-period to predict
        the counterfactual post-period. In production, this would use multiple
        donor units (similar entities not affected by the treatment).

        Args:
            pre_data: Pre-event time series
            post_data: Post-event time series (actual)
            pre_event_days: Pre-event window size
            post_event_days: Post-event window size

        Returns:
            Synthetic control with pre-fit metrics and post predictions
        """
        # Aggregate to daily series
        pre_series = self._aggregate_to_daily_from_tuples(pre_data, pre_event_days)
        post_series = self._aggregate_to_daily_from_tuples(post_data, post_event_days)

        # Build synthetic control using moving average + trend
        # (In production, use more sophisticated donor pool matching)

        # Estimate trend from pre-period
        if len(pre_series) > 3:
            # Linear regression for trend
            X = np.arange(len(pre_series)).reshape(-1, 1)
            y = pre_series

            # Simple linear fit
            slope, intercept = np.polyfit(X.flatten(), y, 1)

            # Calculate fitted values for pre-period
            pre_fitted = slope * X.flatten() + intercept

            # Calculate fit quality
            ss_res = np.sum((y - pre_fitted) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            rmse = np.sqrt(np.mean((y - pre_fitted) ** 2))

            # Project trend into post-period
            post_X = np.arange(len(pre_series), len(pre_series) + len(post_series))
            synthetic_post = slope * post_X + intercept

            # Ensure non-negative predictions
            synthetic_post = np.maximum(synthetic_post, 0)

        else:
            # Not enough data, use mean as baseline
            pre_mean = np.mean(pre_series)
            synthetic_post = np.full(len(post_series), pre_mean)
            r_squared = 0.0
            rmse = np.std(pre_series)

        return {
            "synthetic_post": synthetic_post.tolist(),
            "pre_fit_rmse": rmse,
            "pre_fit_r2": r_squared,
        }

    @staticmethod
    def _aggregate_to_daily(
        data: list[tuple[datetime, float]], lookback_days: int
    ) -> np.ndarray:
        """Aggregate signals to daily time series."""
        # Create daily buckets
        daily_counts = np.zeros(lookback_days)

        for timestamp, confidence in data:
            days_ago = (datetime.now(timezone.utc) - timestamp).days
            if 0 <= days_ago < lookback_days:
                # Aggregate by count * average confidence
                daily_counts[lookback_days - days_ago - 1] += confidence

        return daily_counts

    @staticmethod
    def _aggregate_to_daily_from_tuples(
        data: list[tuple[datetime, float]], window_days: int
    ) -> np.ndarray:
        """Aggregate timestamp-value pairs to daily series."""
        if not data:
            return np.zeros(window_days)

        # Find date range
        dates = [d for d, v in data]
        min_date = min(dates)

        # Create daily buckets
        daily_values = []
        for day_offset in range(window_days):
            target_date = min_date + timedelta(days=day_offset)

            # Aggregate values for this day
            day_values = [v for d, v in data if d.date() == target_date.date()]

            # Use mean if multiple values, 0 if none
            daily_values.append(np.mean(day_values) if day_values else 0.0)

        return np.array(daily_values)

    @staticmethod
    def _interpret_counterfactual_result(
        average_effect: float, pct_impact: float, is_significant: bool
    ) -> str:
        """Generate human-readable interpretation of counterfactual results."""
        if not is_significant:
            return (
                f"No statistically significant impact detected. "
                f"Observed change of {pct_impact:.1f}% could be due to random variation."
            )

        direction = "increased" if average_effect > 0 else "decreased"
        magnitude = abs(pct_impact)

        if magnitude >= 20:
            strength = "substantial"
        elif magnitude >= 10:
            strength = "moderate"
        elif magnitude >= 5:
            strength = "small but significant"
        else:
            strength = "marginal"

        return (
            f"Event caused a {strength} {direction} in outcome metric. "
            f"Actual values were {magnitude:.1f}% {'higher' if average_effect > 0 else 'lower'} "
            f"than counterfactual baseline (p < 0.05)."
        )

    async def difference_in_differences(
        self,
        treatment_group_metric: str,
        control_group_metric: str,
        event_date: datetime,
        *,
        pre_period_days: int = 30,
        post_period_days: int = 30,
    ) -> dict[str, Any]:
        """Difference-in-differences estimation for causal impact.

        Compares change in treatment group vs. control group before/after event.

        Args:
            treatment_group_metric: Metric for treated entities
            control_group_metric: Metric for control entities
            event_date: When treatment occurred
            pre_period_days: Pre-treatment window
            post_period_days: Post-treatment window

        Returns:
            DiD estimate with statistical significance
        """
        # Define time windows
        pre_start = event_date - timedelta(days=pre_period_days)
        post_end = event_date + timedelta(days=post_period_days)

        # Helper function to get average metric value in window
        async def get_avg_metric(metric: str, start: datetime, end: datetime) -> float:
            query = select(Signal.confidence).where(
                and_(
                    Signal.signal_type == metric,
                    Signal.published_at >= start,
                    Signal.published_at <= end,
                )
            )
            result = await self.db.execute(query)
            values = [r.confidence for r in result]
            return np.mean(values) if values else 0.0

        # Get metrics for all four cells
        treatment_pre = await get_avg_metric(
            treatment_group_metric, pre_start, event_date
        )
        treatment_post = await get_avg_metric(
            treatment_group_metric, event_date, post_end
        )
        control_pre = await get_avg_metric(control_group_metric, pre_start, event_date)
        control_post = await get_avg_metric(control_group_metric, event_date, post_end)

        # Calculate DiD estimator
        # DiD = (Treatment_Post - Treatment_Pre) - (Control_Post - Control_Pre)
        treatment_change = treatment_post - treatment_pre
        control_change = control_post - control_pre
        did_estimate = treatment_change - control_change

        # Calculate percentage effect
        pct_effect = (did_estimate / treatment_pre * 100) if treatment_pre != 0 else 0

        return {
            "method": "difference_in_differences",
            "event_date": event_date.isoformat(),
            "did_estimate": round(did_estimate, 4),
            "percentage_effect": round(pct_effect, 2),
            "decomposition": {
                "treatment_change": round(treatment_change, 4),
                "control_change": round(control_change, 4),
            },
            "cell_values": {
                "treatment_pre": round(treatment_pre, 4),
                "treatment_post": round(treatment_post, 4),
                "control_pre": round(control_pre, 4),
                "control_post": round(control_post, 4),
            },
            "interpretation": (
                f"Treatment effect: {abs(pct_effect):.1f}% "
                f"{'increase' if did_estimate > 0 else 'decrease'} "
                f"compared to control group trend"
            ),
        }
