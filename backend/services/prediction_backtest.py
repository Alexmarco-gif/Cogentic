"""Prediction backtest engine — validates causal predictions against reality.

Implements systematic backtesting for Metric 3 (Prediction Accuracy >70%).
Takes historical predictions and compares them with what actually happened
to produce a validated accuracy score.

Methodology:
  1. For each historical causal prediction (event_type X → event_type Y)
  2. Check if event_type Y actually occurred within the predicted timeframe
  3. Score: match = accurate, miss = inaccurate
  4. Aggregate accuracy across all predictions
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.causal_event import CausalEdge, CausalEvent
from backend.models.user_feedback import UserFeedback

logger = logging.getLogger(__name__)


class PredictionBacktestService:
    """Backtests causal predictions against actual outcomes.

    This automates the "Prediction Accuracy >70% on 7-day forecasts"
    success metric. Instead of relying only on user feedback
    (prediction_accurate / prediction_inaccurate), it can systematically
    verify predictions against the event record.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_backtest(
        self,
        *,
        lookback_days: int = 90,
        forecast_horizon_days: int = 7,
        min_edge_confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Run systematic backtest over historical predictions.

        For each causal edge (A → B) discovered before a given point,
        check if event B actually occurred within the forecast window
        after event A.

        Args:
            lookback_days: How far back to test.
            forecast_horizon_days: The prediction window for each forecast.
            min_edge_confidence: Minimum edge confidence to test.

        Returns:
            Backtest results with accuracy and breakdown.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=lookback_days)
        # Only test predictions where the forecast window has fully elapsed
        window_end = now - timedelta(days=forecast_horizon_days)

        # Get causal edges created in the lookback window
        # that have had time for their predictions to materialize
        edges_result = await self.db.execute(
            select(CausalEdge)
            .where(
                and_(
                    CausalEdge.created_at >= cutoff,
                    CausalEdge.created_at <= window_end,
                    CausalEdge.confidence >= min_edge_confidence,
                )
            )
            .order_by(desc(CausalEdge.created_at))
            .limit(500)
        )
        edges = edges_result.scalars().all()

        if not edges:
            return {
                "accuracy_pct": None,
                "total_predictions_tested": 0,
                "accurate": 0,
                "inaccurate": 0,
                "lookback_days": lookback_days,
                "forecast_horizon_days": forecast_horizon_days,
                "note": "No causal predictions found within the lookback window.",
            }

        accurate = 0
        inaccurate = 0
        results_by_type: dict[str, dict] = {}

        for edge in edges:
            # Get the cause event to get its type and timestamp
            cause_event = await self.db.get(CausalEvent, edge.cause_event_id)
            effect_event = await self.db.get(CausalEvent, edge.effect_event_id)

            if not cause_event or not effect_event:
                continue

            predicted_type = effect_event.event_type
            cause_time = cause_event.event_timestamp
            predicted_lag = edge.lag_days_avg

            # Define the forecast window: after cause event, within horizon
            forecast_start = cause_time
            forecast_end = cause_time + timedelta(
                days=max(forecast_horizon_days, predicted_lag + 3)
            )

            # Skip if the forecast window extends into the future
            if forecast_end > now:
                continue

            # Check if a matching effect event actually occurred
            match_result = await self.db.execute(
                select(func.count(CausalEvent.id)).where(
                    and_(
                        CausalEvent.event_type == predicted_type,
                        CausalEvent.event_timestamp >= forecast_start,
                        CausalEvent.event_timestamp <= forecast_end,
                        CausalEvent.id != effect_event.id,  # Don't match self
                    )
                )
            )
            match_count = match_result.scalar() or 0

            is_accurate = match_count > 0

            if is_accurate:
                accurate += 1
            else:
                inaccurate += 1

            # Track by cause->effect type pair
            pair_key = f"{cause_event.event_type} -> {predicted_type}"
            if pair_key not in results_by_type:
                results_by_type[pair_key] = {
                    "tested": 0,
                    "accurate": 0,
                }
            results_by_type[pair_key]["tested"] += 1
            if is_accurate:
                results_by_type[pair_key]["accurate"] += 1

        total = accurate + inaccurate
        accuracy_pct = round(accurate / total * 100, 2) if total > 0 else None

        # Format pair results
        pair_results = []
        for pair, data in sorted(
            results_by_type.items(),
            key=lambda x: x[1]["tested"],
            reverse=True,
        ):
            pair_acc = round(
                data["accurate"] / data["tested"] * 100, 1
            ) if data["tested"] > 0 else 0
            pair_results.append({
                "causal_pair": pair,
                "tested": data["tested"],
                "accurate": data["accurate"],
                "accuracy_pct": pair_acc,
            })

        return {
            "accuracy_pct": accuracy_pct,
            "total_predictions_tested": total,
            "accurate": accurate,
            "inaccurate": inaccurate,
            "lookback_days": lookback_days,
            "forecast_horizon_days": forecast_horizon_days,
            "min_edge_confidence": min_edge_confidence,
            "pair_breakdown": pair_results,
            "data_sufficient": total >= 10,
            "meets_target": accuracy_pct is not None and accuracy_pct >= 70.0,
        }

    async def backtest_specific_chain(
        self,
        cause_event_type: str,
        effect_event_type: str,
        *,
        lookback_days: int = 180,
        forecast_horizon_days: int = 14,
    ) -> dict[str, Any]:
        """Backtest a specific cause → effect chain.

        Finds all historical instances where the cause event occurred,
        checks if the effect followed within the horizon.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        horizon_cutoff = datetime.now(timezone.utc) - timedelta(
            days=forecast_horizon_days
        )

        # Get all cause events within the lookback window
        cause_result = await self.db.execute(
            select(CausalEvent)
            .where(
                and_(
                    CausalEvent.event_type == cause_event_type,
                    CausalEvent.event_timestamp >= cutoff,
                    CausalEvent.event_timestamp <= horizon_cutoff,
                )
            )
            .order_by(CausalEvent.event_timestamp)
        )
        cause_events = cause_result.scalars().all()

        if not cause_events:
            return {
                "cause": cause_event_type,
                "effect": effect_event_type,
                "accuracy_pct": None,
                "instances_tested": 0,
                "note": "No historical instances of cause event found.",
            }

        hits = 0
        misses = 0
        instances = []

        for cause in cause_events:
            window_end = cause.event_timestamp + timedelta(
                days=forecast_horizon_days
            )

            # Check if effect occurred
            match = await self.db.execute(
                select(CausalEvent)
                .where(
                    and_(
                        CausalEvent.event_type == effect_event_type,
                        CausalEvent.event_timestamp > cause.event_timestamp,
                        CausalEvent.event_timestamp <= window_end,
                    )
                )
                .limit(1)
            )
            effect = match.scalars().first()

            if effect:
                hits += 1
                lag = (
                    effect.event_timestamp - cause.event_timestamp
                ).days
                instances.append({
                    "cause_date": cause.event_timestamp.isoformat(),
                    "effect_date": effect.event_timestamp.isoformat(),
                    "lag_days": lag,
                    "result": "hit",
                })
            else:
                misses += 1
                instances.append({
                    "cause_date": cause.event_timestamp.isoformat(),
                    "effect_date": None,
                    "lag_days": None,
                    "result": "miss",
                })

        total = hits + misses
        accuracy_pct = round(hits / total * 100, 2) if total > 0 else None

        return {
            "cause": cause_event_type,
            "effect": effect_event_type,
            "accuracy_pct": accuracy_pct,
            "instances_tested": total,
            "hits": hits,
            "misses": misses,
            "forecast_horizon_days": forecast_horizon_days,
            "avg_lag_days": round(
                sum(
                    i["lag_days"]
                    for i in instances
                    if i["lag_days"] is not None
                )
                / max(hits, 1),
                1,
            ),
            "instances": instances[:20],  # Limit detail
            "meets_target": accuracy_pct is not None and accuracy_pct >= 70.0,
        }

    async def backtest_all_known_chains(
        self,
        *,
        lookback_days: int = 180,
        forecast_horizon_days: int = 7,
        min_edge_confidence: float = 0.6,
        min_observations: int = 2,
    ) -> dict[str, Any]:
        """Backtest all known causal chains with sufficient observations.

        Finds all distinct cause→effect type pairs in the causal edge
        table and backtests each one.
        """
        # Get distinct cause→effect type pairs from edges
        pairs_result = await self.db.execute(
            text("""
                SELECT DISTINCT e1.event_type AS cause_type,
                                e2.event_type AS effect_type
                FROM causal_edges ce
                JOIN causal_events e1 ON ce.cause_event_id = e1.id
                JOIN causal_events e2 ON ce.effect_event_id = e2.id
                WHERE ce.confidence >= :min_conf
                  AND ce.observation_count >= :min_obs
                LIMIT 50
            """),
            {
                "min_conf": min_edge_confidence,
                "min_obs": min_observations,
            },
        )
        chain_pairs: list[tuple[str, str]] = [
            (row[0], row[1]) for row in pairs_result.all()
        ]

        if not chain_pairs:
            return {
                "total_chains_tested": 0,
                "overall_accuracy_pct": None,
                "chain_results": [],
                "note": "No validated causal chains found to backtest.",
            }

        # Backtest each chain
        chain_results = []
        total_hits = 0
        total_tests = 0

        for cause_type, effect_type in chain_pairs[:20]:  # Limit to top 20
            result = await self.backtest_specific_chain(
                cause_type,
                effect_type,
                lookback_days=lookback_days,
                forecast_horizon_days=forecast_horizon_days,
            )
            chain_results.append(result)
            total_hits += result.get("hits", 0)
            total_tests += result.get("instances_tested", 0)

        overall_accuracy = (
            round(total_hits / total_tests * 100, 2) if total_tests > 0 else None
        )

        return {
            "total_chains_tested": len(chain_results),
            "total_predictions_tested": total_tests,
            "total_hits": total_hits,
            "overall_accuracy_pct": overall_accuracy,
            "meets_target": overall_accuracy is not None and overall_accuracy >= 70.0,
            "chain_results": sorted(
                chain_results,
                key=lambda x: x.get("instances_tested", 0),
                reverse=True,
            ),
        }
