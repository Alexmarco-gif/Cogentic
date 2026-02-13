"""Moat metrics service — measures intelligence moat strength.

Implements all 5 success metrics from the Technical Implementation
Moat Strategy document:

  1. Entity Graph Coverage — 1,000+ Nigerian entities (target)
  2. Causal Chains Discovered — 50+ validated chains (target)
  3. Prediction Accuracy — >70% on 7-day forecasts (target)
  4. Replicability Score — <20% ChatGPT-replicable (target)
  5. User Retention (DAU/MAU) — >0.4 (target)

Each metric can be computed in real-time or read from the latest
daily snapshot. Snapshots are stored in moat_metric_snapshots table.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, case, desc, distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.causal_event import CausalEdge, CausalEvent
from backend.models.entity import Entity
from backend.models.entity_alias import EntityAlias
from backend.models.entity_relationship import EntityRelationship
from backend.models.entity_source_profile import EntitySourceProfile
from backend.models.moat_metric import MoatMetricSnapshot
from backend.models.user import User
from backend.models.user_feedback import UserFeedback

logger = logging.getLogger(__name__)

# ── Targets ──────────────────────────────────────────────────────────

TARGETS = {
    "entity_graph_coverage": 1000,  # 1,000+ entities
    "causal_chains_discovered": 50,  # 50+ validated chains
    "prediction_accuracy_pct": 70.0,  # >70%
    "replicability_score_pct": 20.0,  # <20% (lower is better)
    "dau_mau_ratio": 0.4,  # >0.4
}


class MoatMetricsService:
    """Computes, tracks, and reports on all 5 intelligence moat metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Metric 1: Entity Graph Coverage ──────────────────────────────

    async def compute_entity_graph_coverage(self) -> dict[str, Any]:
        """Count entities, verified entities, relationships, and source profiles.

        Target: 1,000+ Nigerian entities in the entity graph.
        """
        result = await self.db.execute(
            select(
                func.count(Entity.id).label("total"),
                func.count(case((Entity.verified.is_(True), 1))).label("verified"),
            )
        )
        row = result.one()
        total = row.total
        verified = row.verified

        # Relationships
        rel_result = await self.db.execute(
            select(func.count(EntityRelationship.id)).where(
                EntityRelationship.is_active.is_(True)
            )
        )
        relationship_count = rel_result.scalar() or 0

        # Source profiles
        sp_result = await self.db.execute(select(func.count(EntitySourceProfile.id)))
        source_profile_count = sp_result.scalar() or 0

        # Aliases
        alias_result = await self.db.execute(select(func.count(EntityAlias.id)))
        alias_count = alias_result.scalar() or 0

        # Entity type breakdown
        type_result = await self.db.execute(
            select(
                Entity.entity_type,
                func.count(Entity.id).label("count"),
            ).group_by(Entity.entity_type)
        )
        type_breakdown = {row.entity_type: row.count for row in type_result}

        # Source profile type breakdown
        sp_type_result = await self.db.execute(
            select(
                EntitySourceProfile.source_type,
                func.count(EntitySourceProfile.id).label("count"),
            ).group_by(EntitySourceProfile.source_type)
        )
        source_breakdown = {row.source_type: row.count for row in sp_type_result}

        target = TARGETS["entity_graph_coverage"]
        progress_pct = round(min(total / target * 100, 100), 1) if target else 0

        return {
            "metric": "entity_graph_coverage",
            "target": target,
            "current": total,
            "progress_pct": progress_pct,
            "meets_target": total >= target,
            "details": {
                "total_entities": total,
                "verified_entities": verified,
                "relationships": relationship_count,
                "source_profiles": source_profile_count,
                "aliases": alias_count,
                "entity_type_breakdown": type_breakdown,
                "source_type_breakdown": source_breakdown,
                "avg_profiles_per_entity": round(
                    source_profile_count / max(total, 1), 2
                ),
                "avg_relationships_per_entity": round(
                    relationship_count / max(total, 1), 2
                ),
            },
        }

    # ── Metric 2: Causal Chains Discovered ───────────────────────────

    async def compute_causal_chains_discovered(self) -> dict[str, Any]:
        """Count causal events, edges, and validated chains.

        Target: 50+ validated chains (edges with confidence >= 0.6).

        A "validated chain" is a causal edge with:
          - confidence >= 0.6
          - observation_count >= 2 (seen more than once)
        """
        # Total events
        event_result = await self.db.execute(select(func.count(CausalEvent.id)))
        event_count = event_result.scalar() or 0

        # Total edges
        edge_result = await self.db.execute(select(func.count(CausalEdge.id)))
        edge_count = edge_result.scalar() or 0

        # Validated chains (high confidence + multiple observations)
        validated_result = await self.db.execute(
            select(func.count(CausalEdge.id)).where(
                and_(
                    CausalEdge.confidence >= 0.6,
                    CausalEdge.observation_count >= 2,
                )
            )
        )
        validated_chain_count = validated_result.scalar() or 0

        # Event category breakdown
        cat_result = await self.db.execute(
            select(
                CausalEvent.event_category,
                func.count(CausalEvent.id).label("count"),
            ).group_by(CausalEvent.event_category)
        )
        category_breakdown = {row.event_category: row.count for row in cat_result}

        # Discovery method breakdown
        method_result = await self.db.execute(
            select(
                CausalEdge.discovery_method,
                func.count(CausalEdge.id).label("count"),
            ).group_by(CausalEdge.discovery_method)
        )
        method_breakdown = {row.discovery_method: row.count for row in method_result}

        # Average confidence of edges
        avg_conf_result = await self.db.execute(select(func.avg(CausalEdge.confidence)))
        avg_edge_confidence = avg_conf_result.scalar() or 0

        # Distinct event type pairs connected by edges
        pair_result = await self.db.execute(
            select(
                func.count(
                    distinct(
                        func.concat(
                            CausalEdge.cause_event_id,
                            "->",
                            CausalEdge.effect_event_id,
                        )
                    )
                )
            )
        )
        unique_connections = pair_result.scalar() or 0

        target = TARGETS["causal_chains_discovered"]
        progress_pct = (
            round(min(validated_chain_count / target * 100, 100), 1) if target else 0
        )

        return {
            "metric": "causal_chains_discovered",
            "target": target,
            "current": validated_chain_count,
            "progress_pct": progress_pct,
            "meets_target": validated_chain_count >= target,
            "details": {
                "total_causal_events": event_count,
                "total_causal_edges": edge_count,
                "validated_chains": validated_chain_count,
                "unique_connections": unique_connections,
                "avg_edge_confidence": round(float(avg_edge_confidence), 4),
                "event_category_breakdown": category_breakdown,
                "discovery_method_breakdown": method_breakdown,
            },
        }

    # ── Metric 3: Prediction Accuracy ────────────────────────────────

    async def compute_prediction_accuracy(
        self, lookback_days: int = 90
    ) -> dict[str, Any]:
        """Compute prediction accuracy from user feedback.

        Target: >70% on 7-day forecasts.

        Uses feedback_type = 'prediction_accurate' and 'prediction_inaccurate'
        as the ground truth signal.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        result = await self.db.execute(
            select(
                func.count(UserFeedback.id).label("total"),
                func.count(
                    case(
                        (
                            UserFeedback.feedback_type == "prediction_accurate",
                            1,
                        ),
                    )
                ).label("accurate"),
                func.count(
                    case(
                        (
                            UserFeedback.feedback_type == "prediction_inaccurate",
                            1,
                        ),
                    )
                ).label("inaccurate"),
            ).where(
                and_(
                    UserFeedback.target_type == "prediction",
                    UserFeedback.created_at >= cutoff,
                )
            )
        )
        row = result.one()

        total = row.total
        accurate = row.accurate
        inaccurate = row.inaccurate
        denominator = accurate + inaccurate

        accuracy_pct = (
            round(accurate / denominator * 100, 2) if denominator > 0 else None
        )

        target = TARGETS["prediction_accuracy_pct"]
        meets_target = accuracy_pct is not None and accuracy_pct >= target

        # Weekly accuracy trend
        weekly_trend = await self._get_prediction_weekly_trend(lookback_days)

        return {
            "metric": "prediction_accuracy",
            "target": target,
            "current": accuracy_pct,
            "progress_pct": (
                round(accuracy_pct / target * 100, 1) if accuracy_pct else 0
            ),
            "meets_target": meets_target,
            "details": {
                "lookback_days": lookback_days,
                "total_validations": total,
                "accurate": accurate,
                "inaccurate": inaccurate,
                "accuracy_pct": accuracy_pct,
                "weekly_trend": weekly_trend,
                "data_sufficient": denominator >= 10,
            },
        }

    async def _get_prediction_weekly_trend(
        self, lookback_days: int
    ) -> list[dict[str, Any]]:
        """Get weekly prediction accuracy trend."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        result = await self.db.execute(
            select(
                func.date_trunc("week", UserFeedback.created_at).label("week"),
                func.count(
                    case(
                        (
                            UserFeedback.feedback_type == "prediction_accurate",
                            1,
                        ),
                    )
                ).label("accurate"),
                func.count(
                    case(
                        (
                            UserFeedback.feedback_type == "prediction_inaccurate",
                            1,
                        ),
                    )
                ).label("inaccurate"),
            )
            .where(
                and_(
                    UserFeedback.target_type == "prediction",
                    UserFeedback.created_at >= cutoff,
                )
            )
            .group_by(func.date_trunc("week", UserFeedback.created_at))
            .order_by(func.date_trunc("week", UserFeedback.created_at))
        )

        trend = []
        for row in result:
            denom = row.accurate + row.inaccurate
            trend.append(
                {
                    "week": row.week.isoformat() if row.week else None,
                    "accurate": row.accurate,
                    "inaccurate": row.inaccurate,
                    "accuracy_pct": (
                        round(row.accurate / denom * 100, 1) if denom > 0 else None
                    ),
                }
            )
        return trend

    # ── Metric 4: Replicability Score ────────────────────────────────

    async def compute_replicability_score(self) -> dict[str, Any]:
        """Compute how much of ESIP's intelligence is replicable by ChatGPT.

        Target: <20% ChatGPT-replicable.

        Methodology:
          Score is calculated by checking which intelligence layers were
          actually applied in synthesis responses. Outputs using only
          basic RAG (no entity graph, no causal data, no feedback) are
          considered fully replicable. Outputs with proprietary layers
          reduce the replicability score.

        The replicability score is estimated from the intelligence_layers
        metadata in synthesis outputs (tracked via user_feedback context).
        """
        # Check feedback entries that have synthesis intelligence layer data
        # in their context field
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)

        # Count synthesis-related feedback with intelligence layer data
        result = await self.db.execute(
            select(
                UserFeedback.context,
            )
            .where(
                and_(
                    UserFeedback.target_type.in_(["signal", "brief"]),
                    UserFeedback.created_at >= cutoff,
                    UserFeedback.context.isnot(None),
                )
            )
            .limit(500)
        )
        rows = result.all()

        total_responses = 0
        responses_with_layers = 0
        layer_counts: dict[str, int] = {
            "entity_graph": 0,
            "causal_predictions": 0,
            "feedback_quality": 0,
            "historical_precedents": 0,
        }

        for (ctx,) in rows:
            if not ctx or not isinstance(ctx, dict):
                continue

            layers = ctx.get("intelligence_layers", [])
            if layers is None:
                continue

            total_responses += 1
            if layers:
                responses_with_layers += 1
                for layer in layers:
                    if layer in layer_counts:
                        layer_counts[layer] += 1

        # If no context data available, fall back to heuristic
        if total_responses == 0:
            return await self._compute_replicability_from_data_coverage()

        # Responses without proprietary layers are replicable
        replicable = total_responses - responses_with_layers
        replicability_pct = round(replicable / total_responses * 100, 1)

        target = TARGETS["replicability_score_pct"]
        meets_target = replicability_pct <= target

        return {
            "metric": "replicability_score",
            "target": target,
            "current": replicability_pct,
            "progress_pct": (
                round(max(0, (target - replicability_pct)) / target * 100, 1)
                if replicability_pct <= target
                else 0
            ),
            "meets_target": meets_target,
            "details": {
                "total_responses_analyzed": total_responses,
                "responses_with_proprietary_layers": responses_with_layers,
                "replicable_responses": replicable,
                "replicability_pct": replicability_pct,
                "layer_usage_counts": layer_counts,
                "methodology": "intelligence_layer_analysis",
            },
        }

    async def _compute_replicability_from_data_coverage(
        self,
    ) -> dict[str, Any]:
        """Heuristic replicability estimate from data asset coverage.

        If ESIP has rich proprietary data, outputs are less replicable.
        Factors:
          - Entity graph depth (source profiles, relationships)
          - Causal chain depth
          - Feedback volume
        """
        # Entity coverage
        entity_result = await self.db.execute(select(func.count(Entity.id)))
        entity_count = entity_result.scalar() or 0

        sp_result = await self.db.execute(select(func.count(EntitySourceProfile.id)))
        source_profiles = sp_result.scalar() or 0

        rel_result = await self.db.execute(
            select(func.count(EntityRelationship.id)).where(
                EntityRelationship.is_active.is_(True)
            )
        )
        relationships = rel_result.scalar() or 0

        # Causal depth
        edge_result = await self.db.execute(
            select(func.count(CausalEdge.id)).where(CausalEdge.confidence >= 0.6)
        )
        causal_edges = edge_result.scalar() or 0

        # Feedback volume
        feedback_result = await self.db.execute(select(func.count(UserFeedback.id)))
        feedback_count = feedback_result.scalar() or 0

        # Score: start at 100% replicable, reduce with proprietary data
        score = 100.0
        # Entity graph reduces replicability
        if entity_count > 0:
            score -= min(entity_count / 20, 20)  # Up to -20%
        if source_profiles > 0:
            score -= min(source_profiles / 10, 15)  # Up to -15%
        if relationships > 0:
            score -= min(relationships / 10, 15)  # Up to -15%
        if causal_edges > 0:
            score -= min(causal_edges / 5, 25)  # Up to -25%
        if feedback_count > 0:
            score -= min(feedback_count / 100, 15)  # Up to -15%

        score = max(score, 5.0)  # Floor at 5%
        replicability_pct = round(score, 1)

        target = TARGETS["replicability_score_pct"]

        return {
            "metric": "replicability_score",
            "target": target,
            "current": replicability_pct,
            "progress_pct": (
                round(max(0, (target - replicability_pct)) / target * 100, 1)
                if replicability_pct <= target
                else 0
            ),
            "meets_target": replicability_pct <= target,
            "details": {
                "methodology": "data_coverage_heuristic",
                "entity_count": entity_count,
                "source_profiles": source_profiles,
                "relationships": relationships,
                "causal_edges": causal_edges,
                "feedback_volume": feedback_count,
                "replicability_pct": replicability_pct,
                "note": (
                    "Using heuristic estimate based on data coverage. "
                    "For precise measurement, run blind testing."
                ),
            },
        }

    # ── Metric 5: User Retention (DAU/MAU) ───────────────────────────

    async def compute_user_retention(self) -> dict[str, Any]:
        """Compute DAU/MAU ratio from user activity.

        Target: >0.4.

        Uses last_login_at from User model and feedback activity to
        measure daily and monthly active users. A user is "active" if
        they either logged in or submitted any feedback/interaction
        within the measurement window.
        """
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        month_ago = now - timedelta(days=30)

        # DAU: users active in last 24 hours
        # From logins
        dau_login = await self.db.execute(
            select(func.count(distinct(User.id))).where(
                and_(
                    User.last_login_at >= day_ago,
                    User.deleted_at.is_(None),
                )
            )
        )
        dau_from_login = dau_login.scalar() or 0

        # From feedback/interactions
        dau_feedback = await self.db.execute(
            select(func.count(distinct(UserFeedback.user_id))).where(
                UserFeedback.created_at >= day_ago
            )
        )
        dau_from_feedback = dau_feedback.scalar() or 0

        # Union DAU (unique users from either source)
        dau_union = await self.db.execute(
            text(
                """
                SELECT COUNT(DISTINCT user_id) FROM (
                    SELECT id AS user_id FROM users
                    WHERE last_login_at >= :day_ago AND deleted_at IS NULL
                    UNION
                    SELECT user_id FROM user_feedback
                    WHERE created_at >= :day_ago
                ) AS active_users
            """
            ),
            {"day_ago": day_ago},
        )
        dau = dau_union.scalar() or 0

        # MAU: users active in last 30 days
        mau_union = await self.db.execute(
            text(
                """
                SELECT COUNT(DISTINCT user_id) FROM (
                    SELECT id AS user_id FROM users
                    WHERE last_login_at >= :month_ago AND deleted_at IS NULL
                    UNION
                    SELECT user_id FROM user_feedback
                    WHERE created_at >= :month_ago
                ) AS active_users
            """
            ),
            {"month_ago": month_ago},
        )
        mau = mau_union.scalar() or 0

        # DAU/MAU ratio
        dau_mau_ratio = round(dau / max(mau, 1), 4) if mau > 0 else None

        # Total registered users
        total_result = await self.db.execute(
            select(func.count(User.id)).where(User.deleted_at.is_(None))
        )
        total_users = total_result.scalar() or 0

        # New users last 30 days
        new_users = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.created_at >= month_ago,
                    User.deleted_at.is_(None),
                )
            )
        )
        new_user_count = new_users.scalar() or 0

        # Weekly DAU trend
        weekly_dau = await self._get_weekly_dau_trend()

        target = TARGETS["dau_mau_ratio"]
        meets_target = dau_mau_ratio is not None and dau_mau_ratio >= target

        return {
            "metric": "user_retention",
            "target": target,
            "current": dau_mau_ratio,
            "progress_pct": (
                round(min(dau_mau_ratio / target * 100, 100), 1) if dau_mau_ratio else 0
            ),
            "meets_target": meets_target,
            "details": {
                "dau": dau,
                "mau": mau,
                "dau_mau_ratio": dau_mau_ratio,
                "total_registered_users": total_users,
                "new_users_30d": new_user_count,
                "dau_breakdown": {
                    "from_login": dau_from_login,
                    "from_feedback": dau_from_feedback,
                },
                "weekly_dau_trend": weekly_dau,
            },
        }

    async def _get_weekly_dau_trend(self) -> list[dict[str, Any]]:
        """Get DAU trend for the past 4 weeks (one data point per week)."""
        trend = []
        now = datetime.now(timezone.utc)

        for weeks_ago in range(4, 0, -1):
            start = now - timedelta(weeks=weeks_ago)
            end = start + timedelta(days=1)

            result = await self.db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT user_id) FROM (
                        SELECT id AS user_id FROM users
                        WHERE last_login_at >= :start AND last_login_at < :end
                          AND deleted_at IS NULL
                        UNION
                        SELECT user_id FROM user_feedback
                        WHERE created_at >= :start AND created_at < :end
                    ) AS active_users
                """
                ),
                {"start": start, "end": end},
            )
            count = result.scalar() or 0
            trend.append(
                {
                    "date": start.strftime("%Y-%m-%d"),
                    "dau": count,
                }
            )

        return trend

    # ── Full Dashboard ───────────────────────────────────────────────

    async def compute_all_metrics(self) -> dict[str, Any]:
        """Compute all 5 moat metrics in one call.

        Returns structured dashboard with overall health score.
        """
        # Compute all metrics
        entity_graph = await self.compute_entity_graph_coverage()
        causal_chains = await self.compute_causal_chains_discovered()
        prediction_acc = await self.compute_prediction_accuracy()
        replicability = await self.compute_replicability_score()
        user_retention = await self.compute_user_retention()

        metrics = [
            entity_graph,
            causal_chains,
            prediction_acc,
            replicability,
            user_retention,
        ]

        # Compute overall health score (0-100)
        health_score = self._compute_health_score(metrics)

        # How many targets met
        targets_met = sum(1 for m in metrics if m.get("meets_target", False))

        return {
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "moat_health_score": health_score,
            "targets_met": f"{targets_met}/{len(metrics)}",
            "overall_status": self._health_status(health_score),
            "metrics": {
                "entity_graph_coverage": entity_graph,
                "causal_chains_discovered": causal_chains,
                "prediction_accuracy": prediction_acc,
                "replicability_score": replicability,
                "user_retention": user_retention,
            },
            "targets": TARGETS,
        }

    @staticmethod
    def _compute_health_score(metrics: list[dict]) -> float:
        """Compute composite moat health score (0-100).

        Weighted:
          - Entity Graph Coverage: 20%
          - Causal Chains: 25%
          - Prediction Accuracy: 25%
          - Replicability Score: 15%
          - User Retention: 15%
        """
        weights = [0.20, 0.25, 0.25, 0.15, 0.15]
        scores = []

        for m in metrics:
            progress = m.get("progress_pct", 0) or 0
            scores.append(min(progress, 100))

        if not scores:
            return 0.0

        weighted = sum(s * w for s, w in zip(scores, weights))
        return round(weighted, 1)

    @staticmethod
    def _health_status(score: float) -> str:
        if score >= 80:
            return "strong"
        elif score >= 60:
            return "growing"
        elif score >= 40:
            return "building"
        elif score >= 20:
            return "nascent"
        else:
            return "critical"

    # ── Snapshot Persistence ─────────────────────────────────────────

    async def take_snapshot(self) -> MoatMetricSnapshot:
        """Compute all metrics and persist as a daily snapshot.

        Returns the created MoatMetricSnapshot instance.
        """
        all_metrics = await self.compute_all_metrics()
        metrics = all_metrics["metrics"]

        eg = metrics["entity_graph_coverage"]
        cc = metrics["causal_chains_discovered"]
        pa = metrics["prediction_accuracy"]
        rs = metrics["replicability_score"]
        ur = metrics["user_retention"]

        snapshot = MoatMetricSnapshot(
            id=uuid4(),
            snapshot_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            # Metric 1
            entity_count=eg["details"]["total_entities"],
            entity_verified_count=eg["details"]["verified_entities"],
            entity_relationship_count=eg["details"]["relationships"],
            entity_source_profile_count=eg["details"]["source_profiles"],
            # Metric 2
            causal_event_count=cc["details"]["total_causal_events"],
            causal_edge_count=cc["details"]["total_causal_edges"],
            causal_chain_count=cc["details"]["validated_chains"],
            # Metric 3
            prediction_total=pa["details"]["total_validations"],
            prediction_accurate=pa["details"]["accurate"],
            prediction_inaccurate=pa["details"]["inaccurate"],
            prediction_accuracy_pct=pa["details"]["accuracy_pct"],
            # Metric 4
            replicability_tests_run=rs["details"].get("total_responses_analyzed", 0),
            replicability_score_pct=rs["details"]["replicability_pct"],
            # Metric 5
            dau=ur["details"]["dau"],
            mau=ur["details"]["mau"],
            dau_mau_ratio=ur["details"]["dau_mau_ratio"],
            # Overall
            moat_health_score=all_metrics["moat_health_score"],
            details={
                "targets_met": all_metrics["targets_met"],
                "overall_status": all_metrics["overall_status"],
                "entity_type_breakdown": eg["details"].get("entity_type_breakdown", {}),
                "causal_category_breakdown": cc["details"].get(
                    "event_category_breakdown", {}
                ),
                "layer_usage": rs["details"].get("layer_usage_counts", {}),
            },
        )

        self.db.add(snapshot)
        await self.db.flush()

        logger.info(
            f"Moat metric snapshot taken: {snapshot.snapshot_date} "
            f"health={snapshot.moat_health_score}"
        )
        return snapshot

    async def get_latest_snapshot(self) -> dict[str, Any] | None:
        """Get the most recent snapshot."""
        result = await self.db.execute(
            select(MoatMetricSnapshot)
            .order_by(desc(MoatMetricSnapshot.created_at))
            .limit(1)
        )
        snapshot = result.scalars().first()
        if not snapshot:
            return None

        return self._snapshot_to_dict(snapshot)

    async def get_snapshot_trend(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily snapshot trend for the past N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(MoatMetricSnapshot)
            .where(MoatMetricSnapshot.created_at >= cutoff)
            .order_by(MoatMetricSnapshot.snapshot_date)
        )
        snapshots = result.scalars().all()

        return [self._snapshot_to_dict(s) for s in snapshots]

    @staticmethod
    def _snapshot_to_dict(snapshot: MoatMetricSnapshot) -> dict[str, Any]:
        return {
            "id": str(snapshot.id),
            "snapshot_date": snapshot.snapshot_date,
            "entity_count": snapshot.entity_count,
            "entity_verified_count": snapshot.entity_verified_count,
            "entity_relationship_count": snapshot.entity_relationship_count,
            "entity_source_profile_count": snapshot.entity_source_profile_count,
            "causal_event_count": snapshot.causal_event_count,
            "causal_edge_count": snapshot.causal_edge_count,
            "causal_chain_count": snapshot.causal_chain_count,
            "prediction_total": snapshot.prediction_total,
            "prediction_accurate": snapshot.prediction_accurate,
            "prediction_inaccurate": snapshot.prediction_inaccurate,
            "prediction_accuracy_pct": snapshot.prediction_accuracy_pct,
            "replicability_tests_run": snapshot.replicability_tests_run,
            "replicability_score_pct": snapshot.replicability_score_pct,
            "dau": snapshot.dau,
            "mau": snapshot.mau,
            "dau_mau_ratio": snapshot.dau_mau_ratio,
            "moat_health_score": snapshot.moat_health_score,
            "details": snapshot.details,
            "created_at": snapshot.created_at.isoformat(),
        }
