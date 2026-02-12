"""Feedback loop service — the network-effect learning engine.

Tracks user interactions and progressively tunes signal relevance,
entity importance, and causal relationship confidence. The more users
engage with ESIP, the smarter it gets — creating an insurmountable
data moat over time.

Network effects:
  - Every signal_useful/signal_not_useful vote improves scoring for ALL users
  - Entity importance scores improve entity resolution accuracy
  - Causal edge confidence is reinforced by collective user validation
  - Dismissed signals train the noise filter for the entire platform
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user_feedback import UserFeedback

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for capturing and leveraging user feedback.

    Feedback types:
      - signal_useful / signal_not_useful: Binary signal quality vote
      - signal_saved / signal_shared: High engagement signals
      - signal_dismissed: Noise indicator
      - brief_helpful / brief_not_helpful: Brief quality feedback
      - entity_relevant / entity_not_relevant: Entity importance signal
      - prediction_accurate / prediction_inaccurate: Causal model validation
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Feedback Capture ─────────────────────────────────────────────

    async def record_feedback(
        self,
        user_id: UUID,
        org_id: UUID,
        feedback_type: str,
        target_type: str,
        target_id: UUID,
        *,
        sentiment: float | None = None,
        comment: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> UserFeedback:
        """Record a user feedback event.

        Args:
            user_id: UUID of the user.
            org_id: UUID of the user's organization.
            feedback_type: One of the supported feedback types.
            target_type: 'signal', 'brief', 'entity', 'prediction'.
            target_id: UUID of the target object.
            sentiment: -1.0 to 1.0 explicit sentiment (optional).
            comment: Free-text comment (optional).
            context: Additional context (device, page, filters active, etc.).

        Returns:
            Created UserFeedback instance.
        """
        # Infer sentiment from feedback_type if not provided
        if sentiment is None:
            sentiment = self._infer_sentiment(feedback_type)

        feedback = UserFeedback(
            id=uuid4(),
            user_id=user_id,
            org_id=org_id,
            feedback_type=feedback_type,
            target_type=target_type,
            target_id=target_id,
            sentiment=sentiment,
            comment=comment[:1000] if comment else None,
            context=context or {},
        )
        self.db.add(feedback)
        await self.db.flush()

        logger.info(
            f"Feedback recorded: user={user_id} type={feedback_type} "
            f"target={target_type}/{target_id}"
        )
        return feedback

    @staticmethod
    def _infer_sentiment(feedback_type: str) -> float:
        """Infer sentiment score from feedback type."""
        SENTIMENT_MAP = {
            "signal_useful": 1.0,
            "signal_not_useful": -1.0,
            "signal_saved": 0.8,
            "signal_shared": 0.9,
            "signal_dismissed": -0.5,
            "brief_helpful": 1.0,
            "brief_not_helpful": -1.0,
            "entity_relevant": 0.8,
            "entity_not_relevant": -0.8,
            "prediction_accurate": 1.0,
            "prediction_inaccurate": -0.8,
        }
        return SENTIMENT_MAP.get(feedback_type, 0.0)

    # ── Aggregated Feedback Queries ──────────────────────────────────

    async def get_signal_quality_score(
        self,
        signal_id: UUID,
    ) -> dict[str, Any]:
        """Get aggregated quality score for a signal based on user feedback.

        Returns a composite signal quality score used to re-rank signals
        in future queries for ALL users — the network effect.
        """
        query = select(
            func.count(UserFeedback.id).label("total_votes"),
            func.count(
                case(
                    (UserFeedback.feedback_type == "signal_useful", 1),
                )
            ).label("useful_votes"),
            func.count(
                case(
                    (UserFeedback.feedback_type == "signal_not_useful", 1),
                )
            ).label("not_useful_votes"),
            func.count(
                case(
                    (UserFeedback.feedback_type == "signal_saved", 1),
                )
            ).label("saves"),
            func.count(
                case(
                    (UserFeedback.feedback_type == "signal_shared", 1),
                )
            ).label("shares"),
            func.count(
                case(
                    (UserFeedback.feedback_type == "signal_dismissed", 1),
                )
            ).label("dismissals"),
            func.avg(UserFeedback.sentiment).label("avg_sentiment"),
        ).where(
            and_(
                UserFeedback.target_type == "signal",
                UserFeedback.target_id == signal_id,
            )
        )

        result = await self.db.execute(query)
        row = result.one()

        total = row.total_votes or 0
        useful = row.useful_votes or 0
        not_useful = row.not_useful_votes or 0
        saves = row.saves or 0
        shares = row.shares or 0
        dismissals = row.dismissals or 0
        avg_sentiment = float(row.avg_sentiment) if row.avg_sentiment else 0.0

        # Composite quality score: weighted combination
        if total == 0:
            quality_score = 0.5  # Neutral default
        else:
            vote_ratio = useful / max(useful + not_useful, 1)
            engagement = min((saves + shares * 2) / max(total, 1), 1.0)
            dismissal_penalty = min(dismissals / max(total, 1), 1.0) * 0.3

            quality_score = round(
                (vote_ratio * 0.5 + engagement * 0.3 + (1 - dismissal_penalty) * 0.2),
                4,
            )

        return {
            "signal_id": str(signal_id),
            "quality_score": quality_score,
            "avg_sentiment": round(avg_sentiment, 4),
            "total_votes": total,
            "useful_votes": useful,
            "not_useful_votes": not_useful,
            "saves": saves,
            "shares": shares,
            "dismissals": dismissals,
        }

    async def get_entity_importance_score(
        self,
        entity_id: UUID,
    ) -> dict[str, Any]:
        """Get importance score for an entity based on collective feedback.

        Entities that users frequently mark as relevant get higher
        importance scores, improving future entity resolution and
        signal ranking.
        """
        query = select(
            func.count(UserFeedback.id).label("total"),
            func.count(
                case(
                    (UserFeedback.feedback_type == "entity_relevant", 1),
                )
            ).label("relevant"),
            func.count(
                case(
                    (UserFeedback.feedback_type == "entity_not_relevant", 1),
                )
            ).label("not_relevant"),
            func.avg(UserFeedback.sentiment).label("avg_sentiment"),
        ).where(
            and_(
                UserFeedback.target_type == "entity",
                UserFeedback.target_id == entity_id,
            )
        )

        result = await self.db.execute(query)
        row = result.one()

        total = row.total or 0
        relevant = row.relevant or 0
        not_relevant = row.not_relevant or 0

        if total == 0:
            importance = 0.5
        else:
            importance = round(
                relevant / max(relevant + not_relevant, 1), 4
            )

        return {
            "entity_id": str(entity_id),
            "importance_score": importance,
            "total_votes": total,
            "relevant_votes": relevant,
            "not_relevant_votes": not_relevant,
        }

    async def get_prediction_accuracy(
        self,
        *,
        lookback_days: int = 90,
    ) -> dict[str, Any]:
        """Get overall prediction accuracy based on user validation.

        Users marking predictions as accurate/inaccurate is the ground-truth
        signal that improves the causal intelligence engine over time.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        query = select(
            func.count(UserFeedback.id).label("total"),
            func.count(
                case(
                    (UserFeedback.feedback_type == "prediction_accurate", 1),
                )
            ).label("accurate"),
            func.count(
                case(
                    (UserFeedback.feedback_type == "prediction_inaccurate", 1),
                )
            ).label("inaccurate"),
        ).where(
            and_(
                UserFeedback.target_type == "prediction",
                UserFeedback.created_at >= cutoff,
            )
        )

        result = await self.db.execute(query)
        row = result.one()

        total = row.total or 0
        accurate = row.accurate or 0
        inaccurate = row.inaccurate or 0

        accuracy = (
            round(accurate / max(accurate + inaccurate, 1), 4)
            if total > 0
            else None
        )

        return {
            "lookback_days": lookback_days,
            "total_validations": total,
            "accurate": accurate,
            "inaccurate": inaccurate,
            "accuracy_rate": accuracy,
        }

    # ── Training Data Generation ─────────────────────────────────────

    async def get_signal_quality_training_data(
        self,
        *,
        min_votes: int = 3,
        lookback_days: int = 180,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        """Generate training data for signal quality model from feedback.

        Returns signals with enough votes to serve as labelled training
        examples for improving the ML signal scoring pipeline.

        This is a key network-effect output: more users voting →
        better training data → better signal quality → better platform.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        query = (
            select(
                UserFeedback.target_id.label("signal_id"),
                func.count(UserFeedback.id).label("total_votes"),
                func.avg(UserFeedback.sentiment).label("avg_sentiment"),
                func.count(
                    case(
                        (UserFeedback.feedback_type == "signal_useful", 1),
                    )
                ).label("useful"),
                func.count(
                    case(
                        (UserFeedback.feedback_type == "signal_not_useful", 1),
                    )
                ).label("not_useful"),
            )
            .where(
                and_(
                    UserFeedback.target_type == "signal",
                    UserFeedback.created_at >= cutoff,
                    UserFeedback.feedback_type.in_(
                        ["signal_useful", "signal_not_useful"]
                    ),
                )
            )
            .group_by(UserFeedback.target_id)
            .having(func.count(UserFeedback.id) >= min_votes)
            .order_by(desc(func.count(UserFeedback.id)))
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        training_data = []
        for row in rows:
            useful = row.useful or 0
            not_useful = row.not_useful or 0
            label = useful / max(useful + not_useful, 1)

            training_data.append({
                "signal_id": str(row.signal_id),
                "label": round(label, 4),
                "total_votes": row.total_votes,
                "avg_sentiment": round(float(row.avg_sentiment or 0), 4),
            })

        logger.info(
            f"Generated {len(training_data)} signal quality training examples"
        )
        return training_data

    # ── Trending Insights from Feedback ──────────────────────────────

    async def get_trending_signals(
        self,
        org_id: UUID | None = None,
        *,
        hours: int = 24,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get signals trending by engagement (saves, shares, useful votes).

        This provides "What's hot across ESIP users" — a collective
        intelligence layer that individual users cannot replicate alone.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        conditions = [
            UserFeedback.target_type == "signal",
            UserFeedback.created_at >= cutoff,
            UserFeedback.feedback_type.in_(
                ["signal_useful", "signal_saved", "signal_shared"]
            ),
        ]

        query = (
            select(
                UserFeedback.target_id.label("signal_id"),
                func.count(UserFeedback.id).label("engagement_count"),
                func.count(
                    func.distinct(UserFeedback.user_id)
                ).label("unique_users"),
                func.count(
                    func.distinct(UserFeedback.org_id)
                ).label("unique_orgs"),
            )
            .where(and_(*conditions))
            .group_by(UserFeedback.target_id)
            .order_by(desc(func.count(UserFeedback.id)))
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "signal_id": str(row.signal_id),
                "engagement_count": row.engagement_count,
                "unique_users": row.unique_users,
                "unique_orgs": row.unique_orgs,
                "virality_score": round(
                    row.unique_orgs / max(row.unique_users, 1), 4
                ),
            }
            for row in rows
        ]

    # ── Feedback Summary for User ────────────────────────────────────

    async def get_user_feedback_summary(
        self,
        user_id: UUID,
        *,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get a summary of a user's feedback activity."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(
            UserFeedback.feedback_type,
            func.count(UserFeedback.id).label("count"),
        ).where(
            and_(
                UserFeedback.user_id == user_id,
                UserFeedback.created_at >= cutoff,
            )
        ).group_by(UserFeedback.feedback_type)

        result = await self.db.execute(query)
        rows = result.all()

        counts = {row.feedback_type: row.count for row in rows}
        total = sum(counts.values())

        return {
            "user_id": str(user_id),
            "period_days": days,
            "total_feedback_events": total,
            "breakdown": counts,
        }
