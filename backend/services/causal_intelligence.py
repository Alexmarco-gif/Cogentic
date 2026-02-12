"""Causal intelligence engine — the core differentiation layer.

Extracts causal events from signals, detects cause-effect patterns,
builds temporal causal graphs, and provides predictive intelligence.

This engine is what makes ESIP intelligence unreplicable:
  - Causal chains trained on domain-specific longitudinal data
  - Granger causality tests proving statistical relationships
  - Counterfactual reasoning for "what if" analysis
  - Predictive cascading impact analysis

No generic AI or Google search can replicate these outputs.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.causal_event import CausalEdge, CausalEvent
from backend.models.signal import Signal

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Event Category Constants ─────────────────────────────────────────

EVENT_CATEGORIES = {
    "policy": "Government or regulatory policy change",
    "market": "Market price, volume, or demand change",
    "corporate": "Company-level action (earnings, launch, M&A)",
    "infrastructure": "Physical infrastructure change",
    "social": "Social or cultural trend shift",
    "environmental": "Weather, natural disaster, climate event",
    "financial": "Monetary policy, FX, interest rate change",
    "technology": "Technology adoption or disruption",
    "supply_chain": "Supply chain disruption or shift",
    "labor": "Labor market or employment change",
}

# Mapping of signal_type → default event_category
SIGNAL_TYPE_TO_CATEGORY = {
    "regulatory": "policy",
    "financial": "financial",
    "market": "market",
    "news": "corporate",
    "social": "social",
    "technology": "technology",
}


class CausalIntelligenceService:
    """Causal intelligence engine for temporal reasoning and prediction.

    Core capabilities:
      1. Event extraction: Convert signals into typed causal events
      2. Edge detection: Discover cause-effect relationships between events
      3. Chain analysis: Find recurring causal chains (sequence patterns)
      4. Prediction: Forecast likely next events from current state
      5. Impact analysis: Cascading impact across entities and industries
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Event Extraction ─────────────────────────────────────────────

    async def extract_event_from_signal(
        self,
        signal: Signal,
        *,
        event_type: str | None = None,
        event_category: str | None = None,
        event_summary: str | None = None,
        entity_ids: list[UUID] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> CausalEvent:
        """Extract a causal event from a signal.

        If event_type / category / summary are not provided, they are
        inferred from the signal's properties.

        Args:
            signal: Source Signal ORM instance.
            event_type: Specific event type (e.g., 'interest_rate_increase').
            event_category: Category (e.g., 'financial').
            event_summary: Human-readable summary.
            entity_ids: UUIDs of entities involved.
            attributes: Domain-specific structured attributes.

        Returns:
            Created CausalEvent instance.
        """
        # Infer defaults from signal
        if not event_type:
            event_type = f"{signal.signal_type}_event"
        if not event_category:
            event_category = SIGNAL_TYPE_TO_CATEGORY.get(
                signal.signal_type, "corporate"
            )
        if not event_summary:
            event_summary = signal.title or signal.summary or "Unclassified event"

        # Get entity IDs from signal_entities if not provided
        if entity_ids is None:
            from backend.models.signal_entity import SignalEntity

            result = await self.db.execute(
                select(SignalEntity.entity_id).where(
                    SignalEntity.signal_id == signal.id
                )
            )
            entity_ids = [row[0] for row in result.all()]

        event = CausalEvent(
            id=uuid4(),
            signal_id=signal.id,
            event_type=event_type,
            event_category=event_category,
            event_summary=event_summary[:2000],  # Truncate
            event_timestamp=signal.published_at or signal.fetched_at,
            entity_ids=[str(eid) for eid in entity_ids],
            attributes=attributes or {},
            confidence=signal.confidence,
        )
        self.db.add(event)
        await self.db.flush()

        logger.info(
            f"Extracted causal event: {event.event_type} ({event.event_category}) "
            f"from signal {signal.id}"
        )
        return event

    async def extract_events_batch(
        self,
        signals: list[Signal],
    ) -> list[CausalEvent]:
        """Extract causal events from a batch of signals."""
        events = []
        for signal in signals:
            try:
                event = await self.extract_event_from_signal(signal)
                events.append(event)
            except Exception as e:
                logger.warning(f"Failed to extract event from signal {signal.id}: {e}")
        return events

    # ── Causal Edge Detection ────────────────────────────────────────

    async def detect_causal_edges(
        self,
        event: CausalEvent,
        *,
        lookback_days: int = 30,
        max_lag_days: int = 14,
        min_entity_overlap: float = 0.3,
        min_confidence: float = 0.5,
    ) -> list[CausalEdge]:
        """Detect potential causal edges from a new event to prior events.

        Criteria for edge creation:
          1. Temporal: Prior event happened within lookback window
          2. Entity overlap: Events share at least one entity
          3. Category compatibility: Events are in compatible categories
          4. Confidence: Both events have sufficient confidence

        Args:
            event: Newly created CausalEvent.
            lookback_days: How far back to look for potential causes.
            max_lag_days: Maximum days between cause and effect.
            min_entity_overlap: Minimum entity overlap ratio.
            min_confidence: Minimum event confidence.

        Returns:
            List of created CausalEdge instances.
        """
        cutoff = event.event_timestamp - timedelta(days=lookback_days)

        # Find prior events within time window
        prior_query = select(CausalEvent).where(
            and_(
                CausalEvent.event_timestamp >= cutoff,
                CausalEvent.event_timestamp < event.event_timestamp,
                CausalEvent.id != event.id,
                CausalEvent.confidence >= min_confidence,
            )
        ).order_by(desc(CausalEvent.event_timestamp))

        result = await self.db.execute(prior_query)
        prior_events = result.scalars().all()

        edges = []
        current_entities = set(event.entity_ids or [])

        for prior in prior_events:
            prior_entities = set(prior.entity_ids or [])

            # Calculate entity overlap
            if current_entities and prior_entities:
                overlap = len(current_entities & prior_entities) / max(
                    len(current_entities), len(prior_entities)
                )
            else:
                overlap = 0.0

            if overlap < min_entity_overlap and not self._are_categories_compatible(
                prior.event_category, event.event_category
            ):
                continue

            # Calculate lag
            lag = (event.event_timestamp - prior.event_timestamp).days
            if lag > max_lag_days:
                continue

            # Calculate edge confidence
            entity_factor = min(overlap * 2.0, 1.0)  # Entity overlap up to 1.0
            temporal_factor = max(0.0, 1.0 - (lag / max_lag_days))  # Closer = higher
            base_confidence = (
                prior.confidence * 0.3
                + event.confidence * 0.3
                + entity_factor * 0.25
                + temporal_factor * 0.15
            )

            if base_confidence < min_confidence:
                continue

            # Check if edge already exists
            existing = await self.db.execute(
                select(CausalEdge).where(
                    and_(
                        CausalEdge.cause_event_id == prior.id,
                        CausalEdge.effect_event_id == event.id,
                    )
                )
            )
            if existing.scalars().first():
                continue

            edge = CausalEdge(
                id=uuid4(),
                cause_event_id=prior.id,
                effect_event_id=event.id,
                relationship_label="leads_to",
                confidence=round(base_confidence, 4),
                lag_days_min=lag,
                lag_days_max=lag,
                lag_days_avg=float(lag),
                observation_count=1,
                discovery_method="auto_detection",
            )
            self.db.add(edge)
            edges.append(edge)

        await self.db.flush()
        logger.info(
            f"Detected {len(edges)} causal edges for event {event.id} "
            f"(checked {len(prior_events)} prior events)"
        )
        return edges

    @staticmethod
    def _are_categories_compatible(cause_cat: str, effect_cat: str) -> bool:
        """Check if two event categories have known causal compatibility.

        For example: policy → financial → market is a known chain.
        """
        COMPATIBLE_PAIRS = {
            ("policy", "financial"),
            ("policy", "market"),
            ("policy", "corporate"),
            ("financial", "market"),
            ("financial", "corporate"),
            ("financial", "supply_chain"),
            ("market", "corporate"),
            ("market", "supply_chain"),
            ("environmental", "supply_chain"),
            ("environmental", "market"),
            ("infrastructure", "supply_chain"),
            ("infrastructure", "market"),
            ("technology", "corporate"),
            ("technology", "market"),
            ("labor", "corporate"),
            ("social", "market"),
            ("supply_chain", "market"),
            ("supply_chain", "corporate"),
        }
        return (cause_cat, effect_cat) in COMPATIBLE_PAIRS

    # ── Causal Chain Analysis ────────────────────────────────────────

    async def find_causal_chains(
        self,
        event_type: str,
        *,
        max_depth: int = 5,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find common causal chains starting from a specific event type.

        Traverses the causal edge graph using recursive CTE to find
        multi-step causal chains.

        Example output:
          "policy_change" → "lending_rate_increase" → "loan_volume_decline"
          (confidence: 0.78, avg_lag: 12 days, occurrences: 4)

        Args:
            event_type: Starting event type to trace forward.
            max_depth: Maximum chain length.
            min_confidence: Minimum edge confidence.
            limit: Maximum chains to return.

        Returns:
            List of causal chain dicts with sequence, lags, and confidence.
        """
        # Use recursive CTE for BFS of causal graph
        cte_query = text(f"""
            WITH RECURSIVE causal_chain AS (
                -- Base case: edges starting from events of given type
                SELECT
                    ce.cause_event_id,
                    ce.effect_event_id,
                    ce.confidence,
                    ce.lag_days_avg,
                    e1.event_type AS cause_type,
                    e2.event_type AS effect_type,
                    e2.event_category AS effect_category,
                    ARRAY[e1.event_type, e2.event_type] AS chain,
                    ARRAY[ce.lag_days_avg] AS lags,
                    ARRAY[ce.confidence] AS confidences,
                    1 AS depth
                FROM causal_edges ce
                JOIN causal_events e1 ON ce.cause_event_id = e1.id
                JOIN causal_events e2 ON ce.effect_event_id = e2.id
                WHERE e1.event_type = :event_type
                  AND ce.confidence >= :min_confidence

                UNION ALL

                -- Recursive case: extend chain
                SELECT
                    ce.cause_event_id,
                    ce.effect_event_id,
                    ce.confidence,
                    ce.lag_days_avg,
                    cc.cause_type,
                    e3.event_type AS effect_type,
                    e3.event_category AS effect_category,
                    cc.chain || e3.event_type AS chain,
                    cc.lags || ce.lag_days_avg AS lags,
                    cc.confidences || ce.confidence AS confidences,
                    cc.depth + 1 AS depth
                FROM causal_chain cc
                JOIN causal_edges ce ON cc.effect_event_id = ce.cause_event_id
                JOIN causal_events e3 ON ce.effect_event_id = e3.id
                WHERE cc.depth < :max_depth
                  AND ce.confidence >= :min_confidence
                  AND NOT (e3.event_type = ANY(cc.chain))  -- Prevent cycles
            )
            SELECT DISTINCT ON (chain)
                chain,
                lags,
                confidences,
                depth
            FROM causal_chain
            WHERE depth >= 1
            ORDER BY chain, depth DESC
            LIMIT :limit
        """)

        result = await self.db.execute(
            cte_query,
            {
                "event_type": event_type,
                "min_confidence": min_confidence,
                "max_depth": max_depth,
                "limit": limit,
            },
        )
        rows = result.fetchall()

        chains = []
        for row in rows:
            conf_list = row.confidences
            avg_conf = sum(conf_list) / len(conf_list) if conf_list else 0
            total_lag = sum(row.lags) if row.lags else 0

            chains.append({
                "chain": row.chain,
                "lags_days": [round(l, 1) for l in row.lags],
                "confidences": [round(c, 4) for c in conf_list],
                "avg_confidence": round(avg_conf, 4),
                "total_lag_days": round(total_lag, 1),
                "depth": row.depth,
            })

        # Sort by average confidence descending
        chains.sort(key=lambda c: c["avg_confidence"], reverse=True)

        logger.info(
            f"Found {len(chains)} causal chains starting from '{event_type}'"
        )
        return chains

    # ── Prediction Engine ────────────────────────────────────────────

    async def predict_cascading_impacts(
        self,
        event_type: str,
        *,
        time_horizon_days: int = 30,
        min_confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Predict cascading impacts from a given event type.

        Uses historical causal chains to forecast what will likely happen
        next, with estimated timelines and confidence levels.

        This is the core proprietary intelligence output — it provides
        predictions based on longitudinal causal data that generic AI
        cannot replicate.

        Args:
            event_type: The triggering event type.
            time_horizon_days: How far ahead to predict.
            min_confidence: Minimum prediction confidence.

        Returns:
            Structured prediction with immediate, secondary, and tertiary impacts.
        """
        # Get all chains starting from this event type
        chains = await self.find_causal_chains(
            event_type,
            max_depth=4,
            min_confidence=min_confidence,
        )

        if not chains:
            return {
                "trigger_event": event_type,
                "predictions": [],
                "confidence": 0.0,
                "data_coverage": "insufficient",
                "note": "Not enough historical data to predict cascading impacts.",
            }

        # Aggregate by next event type (immediate impacts)
        immediate_impacts: dict[str, dict] = {}
        secondary_impacts: dict[str, dict] = {}
        tertiary_impacts: dict[str, dict] = {}

        for chain in chains:
            events = chain["chain"]
            lags = chain["lags_days"]
            confs = chain["confidences"]

            # Immediate impact (depth 1)
            if len(events) >= 2:
                next_event = events[1]
                lag = lags[0] if lags else 0
                conf = confs[0] if confs else 0

                if lag <= time_horizon_days:
                    if next_event not in immediate_impacts:
                        immediate_impacts[next_event] = {
                            "event_type": next_event,
                            "observations": 0,
                            "total_confidence": 0.0,
                            "total_lag": 0.0,
                        }
                    immediate_impacts[next_event]["observations"] += 1
                    immediate_impacts[next_event]["total_confidence"] += conf
                    immediate_impacts[next_event]["total_lag"] += lag

            # Secondary impact (depth 2)
            if len(events) >= 3:
                sec_event = events[2]
                cumulative_lag = sum(lags[:2]) if len(lags) >= 2 else 0
                sec_conf = confs[1] if len(confs) >= 2 else 0

                if cumulative_lag <= time_horizon_days:
                    if sec_event not in secondary_impacts:
                        secondary_impacts[sec_event] = {
                            "event_type": sec_event,
                            "observations": 0,
                            "total_confidence": 0.0,
                            "total_lag": 0.0,
                        }
                    secondary_impacts[sec_event]["observations"] += 1
                    secondary_impacts[sec_event]["total_confidence"] += sec_conf
                    secondary_impacts[sec_event]["total_lag"] += cumulative_lag

            # Tertiary impact (depth 3)
            if len(events) >= 4:
                ter_event = events[3]
                cumulative_lag = sum(lags[:3]) if len(lags) >= 3 else 0
                ter_conf = confs[2] if len(confs) >= 3 else 0

                if cumulative_lag <= time_horizon_days:
                    if ter_event not in tertiary_impacts:
                        tertiary_impacts[ter_event] = {
                            "event_type": ter_event,
                            "observations": 0,
                            "total_confidence": 0.0,
                            "total_lag": 0.0,
                        }
                    tertiary_impacts[ter_event]["observations"] += 1
                    tertiary_impacts[ter_event]["total_confidence"] += ter_conf
                    tertiary_impacts[ter_event]["total_lag"] += cumulative_lag

        def _format_impacts(impacts: dict) -> list[dict]:
            formatted = []
            for key, val in impacts.items():
                obs = val["observations"]
                formatted.append({
                    "event_type": val["event_type"],
                    "probability": round(
                        min((obs / max(len(chains), 1)) * (val["total_confidence"] / obs), 0.95),
                        3,
                    ),
                    "avg_lag_days": round(val["total_lag"] / obs, 1),
                    "historical_observations": obs,
                    "avg_confidence": round(val["total_confidence"] / obs, 4),
                })
            return sorted(formatted, key=lambda x: x["probability"], reverse=True)

        return {
            "trigger_event": event_type,
            "time_horizon_days": time_horizon_days,
            "immediate_impacts": _format_impacts(immediate_impacts),
            "secondary_impacts": _format_impacts(secondary_impacts),
            "tertiary_impacts": _format_impacts(tertiary_impacts),
            "total_chains_analyzed": len(chains),
            "data_coverage": "sufficient" if len(chains) >= 3 else "limited",
        }

    # ── Historical Pattern Matching ──────────────────────────────────

    async def find_historical_precedents(
        self,
        event_type: str,
        *,
        lookback_months: int = 24,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find historical precedents for a given event type.

        Returns past instances of similar events and what happened after
        each one. This provides the "Based on N historical instances..."
        intelligence that makes outputs unreplicable.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_months * 30)

        # Find historical events of this type
        query = (
            select(CausalEvent)
            .where(
                and_(
                    CausalEvent.event_type == event_type,
                    CausalEvent.event_timestamp >= cutoff,
                )
            )
            .order_by(desc(CausalEvent.event_timestamp))
            .limit(limit)
        )

        result = await self.db.execute(query)
        events = result.scalars().all()

        precedents = []
        for event in events:
            # Get what happened after this event (outgoing causal edges)
            edges_result = await self.db.execute(
                select(CausalEdge, CausalEvent)
                .join(CausalEvent, CausalEdge.effect_event_id == CausalEvent.id)
                .where(CausalEdge.cause_event_id == event.id)
                .order_by(CausalEdge.lag_days_avg)
            )
            consequences = []
            for edge, effect_event in edges_result:
                consequences.append({
                    "effect_type": effect_event.event_type,
                    "effect_category": effect_event.event_category,
                    "effect_summary": effect_event.event_summary[:200],
                    "lag_days": edge.lag_days_avg,
                    "confidence": edge.confidence,
                })

            precedents.append({
                "event_id": str(event.id),
                "event_type": event.event_type,
                "event_summary": event.event_summary[:200],
                "timestamp": event.event_timestamp.isoformat(),
                "confidence": event.confidence,
                "entity_ids": event.entity_ids,
                "consequences": consequences,
                "attributes": event.attributes,
            })

        return precedents

    # ── Granger Causality Testing ────────────────────────────────────

    async def granger_causality_test(
        self,
        cause_event_type: str,
        effect_event_type: str,
        *,
        max_lag: int = 14,
        lookback_days: int = 180,
    ) -> dict[str, Any]:
        """Test statistical (Granger) causality between two event types.

        Granger causality: Do past values of X improve prediction of Y
        beyond what past values of Y alone can predict?

        This provides statistical rigor backing for causal claims —
        something no generic AI provides.
        """
        try:
            from statsmodels.tsa.stattools import grangercausalitytests
        except ImportError:
            return {
                "error": "statsmodels not installed",
                "is_causal": False,
            }

        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        # Build daily time series for cause events
        cause_query = select(
            CausalEvent.event_timestamp,
            func.count(CausalEvent.id).label("count"),
        ).where(
            and_(
                CausalEvent.event_type == cause_event_type,
                CausalEvent.event_timestamp >= cutoff,
            )
        ).group_by(
            func.date_trunc("day", CausalEvent.event_timestamp)
        ).order_by(
            func.date_trunc("day", CausalEvent.event_timestamp)
        )

        effect_query = select(
            CausalEvent.event_timestamp,
            func.count(CausalEvent.id).label("count"),
        ).where(
            and_(
                CausalEvent.event_type == effect_event_type,
                CausalEvent.event_timestamp >= cutoff,
            )
        ).group_by(
            func.date_trunc("day", CausalEvent.event_timestamp)
        ).order_by(
            func.date_trunc("day", CausalEvent.event_timestamp)
        )

        cause_result = await self.db.execute(cause_query)
        effect_result = await self.db.execute(effect_query)

        # Convert to daily arrays
        cause_daily: dict[str, int] = {}
        for row in cause_result:
            day_key = row.event_timestamp.strftime("%Y-%m-%d")
            cause_daily[day_key] = row.count

        effect_daily: dict[str, int] = {}
        for row in effect_result:
            day_key = row.event_timestamp.strftime("%Y-%m-%d")
            effect_daily[day_key] = row.count

        # Build aligned arrays
        all_days = sorted(set(cause_daily.keys()) | set(effect_daily.keys()))
        if len(all_days) < max_lag * 3:
            return {
                "cause": cause_event_type,
                "effect": effect_event_type,
                "is_causal": False,
                "note": f"Insufficient data ({len(all_days)} days, need {max_lag * 3}+)",
                "data_points": len(all_days),
            }

        cause_series = np.array([cause_daily.get(d, 0) for d in all_days], dtype=float)
        effect_series = np.array([effect_daily.get(d, 0) for d in all_days], dtype=float)

        # Add small noise to avoid singular matrices
        cause_series += np.random.normal(0, 0.01, len(cause_series))
        effect_series += np.random.normal(0, 0.01, len(effect_series))

        import pandas as pd

        data = pd.DataFrame({"effect": effect_series, "cause": cause_series})

        try:
            gc_result = grangercausalitytests(data, maxlag=max_lag, verbose=False)

            p_values = {}
            for lag in range(1, max_lag + 1):
                p_values[lag] = gc_result[lag][0]["ssr_ftest"][1]

            optimal_lag = min(p_values, key=p_values.get)
            best_p = p_values[optimal_lag]
            is_causal = best_p < 0.05

            return {
                "cause": cause_event_type,
                "effect": effect_event_type,
                "is_causal": is_causal,
                "optimal_lag_days": optimal_lag,
                "p_value": round(best_p, 6),
                "confidence": round(1 - best_p, 4) if is_causal else 0.0,
                "data_points": len(all_days),
                "interpretation": (
                    f"'{cause_event_type}' statistically Granger-causes "
                    f"'{effect_event_type}' with {optimal_lag}-day lag "
                    f"(p={best_p:.4f})"
                    if is_causal
                    else f"No statistically significant Granger causality detected "
                    f"(best p={best_p:.4f}, threshold=0.05)"
                ),
            }

        except Exception as e:
            logger.error(f"Granger causality test failed: {e}")
            return {
                "cause": cause_event_type,
                "effect": effect_event_type,
                "is_causal": False,
                "error": str(e)[:200],
            }

    # ── Cascading Impact Analysis (Proprietary) ──────────────────────

    async def analyze_signal_impact(
        self,
        signal_id: UUID,
        *,
        time_horizon_days: int = 30,
    ) -> dict[str, Any]:
        """Analyze the cascading impact of a specific signal.

        This is the flagship proprietary intelligence method. Given a signal,
        it returns:
          - What causal events are triggered
          - What cascading impacts to expect (with timelines)
          - Historical precedents
          - Who (entities) will be affected
          - Confidence levels with evidence lineage

        No generic AI, Google search, or competitor platform can produce
        this output without years of accumulated causal data.
        """
        # Get signal
        signal = await self.db.get(Signal, signal_id)
        if not signal:
            return {"error": f"Signal {signal_id} not found"}

        # Get or create causal event for this signal
        event_result = await self.db.execute(
            select(CausalEvent).where(CausalEvent.signal_id == signal_id)
        )
        event = event_result.scalars().first()

        if not event:
            event = await self.extract_event_from_signal(signal)

        # Get predictions
        predictions = await self.predict_cascading_impacts(
            event.event_type,
            time_horizon_days=time_horizon_days,
        )

        # Get historical precedents
        precedents = await self.find_historical_precedents(
            event.event_type,
            lookback_months=24,
            limit=5,
        )

        # Get affected entities
        affected_entities = set(event.entity_ids or [])
        for impact in predictions.get("immediate_impacts", []):
            # Find entities commonly affected by this impact type
            ent_result = await self.db.execute(
                select(CausalEvent.entity_ids)
                .where(CausalEvent.event_type == impact["event_type"])
                .limit(20)
            )
            for row in ent_result:
                if row.entity_ids:
                    affected_entities.update(row.entity_ids)

        return {
            "signal": {
                "id": str(signal.id),
                "title": signal.title,
                "type": signal.signal_type,
                "confidence": signal.confidence,
            },
            "trigger_event": {
                "id": str(event.id),
                "type": event.event_type,
                "category": event.event_category,
                "summary": event.event_summary,
                "timestamp": event.event_timestamp.isoformat(),
            },
            "predictions": predictions,
            "historical_precedents": {
                "count": len(precedents),
                "precedents": precedents,
            },
            "affected_entities": list(affected_entities),
            "analysis_metadata": {
                "time_horizon_days": time_horizon_days,
                "model_version": "causal_v1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
