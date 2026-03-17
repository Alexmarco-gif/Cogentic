"""ML scoring service.

Computes anomaly, trending, and confidence scores for signals.
Runs as RQ worker jobs (async, non-blocking).

Day-1 Models:
  - anomaly_detector: Isolation Forest → anomaly score (0..1)
  - trending_scorer: Time-series slope on signal volume → trending score
  - confidence_calibrator: Logistic regression on 4 features → calibrated confidence
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.ml.inference import get_inference_engine
from backend.models.ml_model_run import MLModelRun
from backend.models.signal import Signal
from backend.repositories.ml_model_run import MLModelRunRepository
from backend.repositories.signal_score import SignalScoreRepository

logger = logging.getLogger(__name__)
settings = get_settings()

# Feature extraction constants
SOURCE_TYPE_MAP = {"api": 0, "rss": 1, "scraper": 2, "social": 3}


class ScoringService:
    """ML scoring pipeline that runs all 3 models on signals.

    Pipeline per signal:
      1. Extract features
      2. Run anomaly detector → anomaly score
      3. Run trending scorer → trending score
      4. Run confidence calibrator → calibrated confidence
      5. Store scores in SignalScore table
      6. Audit run in MLModelRun table

    Falls back to heuristic scoring if ONNX models aren't trained yet.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = get_inference_engine()
        self.score_repo = SignalScoreRepository(db)
        self.run_repo = MLModelRunRepository(db)

    async def score_signal(self, signal: Signal) -> dict[str, float]:
        """Score a single signal with all 3 models.

        Args:
            signal: Signal ORM instance.

        Returns:
            Dict with score_type → score_value.
        """
        scores: dict[str, float] = {}

        # Anomaly score
        try:
            anomaly = await self._score_anomaly(signal)
            scores["anomaly"] = anomaly
        except Exception as e:
            logger.warning(f"Anomaly scoring failed for {signal.id}: {e}")
            scores["anomaly"] = await self._heuristic_anomaly(signal)

        # Trending score
        try:
            trending = await self._score_trending(signal)
            scores["trending"] = trending
        except Exception as e:
            logger.warning(f"Trending scoring failed for {signal.id}: {e}")
            scores["trending"] = 0.5

        # Confidence score
        try:
            confidence = await self._score_confidence(signal)
            scores["confidence"] = confidence
        except Exception as e:
            logger.warning(f"Confidence scoring failed for {signal.id}: {e}")
            scores["confidence"] = signal.confidence  # keep original

        return scores

    async def score_batch(self, signals: list[Signal]) -> dict[str, Any]:
        """Score a batch of signals and persist results.

        Creates an MLModelRun audit record for the batch.

        Args:
            signals: List of Signal ORM instances.

        Returns:
            Summary dict with counts and timing.
        """
        if not signals:
            return {"scored": 0, "errors": 0}

        start = time.monotonic()
        scored = 0
        errors = 0

        # Create model run audit record
        model_run = await self._create_model_run(
            model_name="scoring_pipeline",
            model_version="1.0",
            signals_count=len(signals),
        )

        for signal in signals:
            try:
                scores = await self.score_signal(signal)

                # Persist each score
                for score_type, score_value in scores.items():
                    await self.score_repo.upsert_score(
                        signal_id=signal.id,
                        score_type=score_type,
                        score_value=round(score_value, 4),
                        model_run_id=model_run.id,
                    )

                # Update signal confidence with calibrated value
                if "confidence" in scores:
                    signal.confidence = round(scores["confidence"], 4)

                scored += 1

            except Exception as e:
                errors += 1
                logger.error(f"Scoring failed for signal {signal.id}: {e}")

        # Finalize model run
        duration_ms = int((time.monotonic() - start) * 1000)
        model_run.status = "completed"
        model_run.signals_processed = scored
        model_run.duration_ms = duration_ms
        model_run.output_json = {"scored": scored, "errors": errors}
        await self.db.flush()

        logger.info(
            f"Scoring batch complete: {scored}/{len(signals)} scored, "
            f"{errors} errors, {duration_ms}ms"
        )

        return {
            "scored": scored,
            "errors": errors,
            "duration_ms": duration_ms,
            "model_run_id": str(model_run.id),
        }

    # ── Anomaly Scoring ──────────────────────────────────────────────

    async def _score_anomaly(self, signal: Signal) -> float:
        """Score anomaly using Isolation Forest ONNX model.

        Features: [content_length, hour_of_day, day_of_week, source_type_encoded]

        Isolation Forest returns decision_function scores:
          - Negative = more anomalous
          - Positive = normal
        We normalize to 0..1 where 1 = most anomalous.

        Falls back to heuristic scoring on timeout or error.
        """
        if not self.engine.is_model_available("anomaly_detector"):
            return await self._heuristic_anomaly(signal)

        try:
            features = self._extract_anomaly_features(signal)
            raw_scores = self.engine.predict("anomaly_detector", features)

            # Isolation Forest decision_function: negative = anomaly
            # Normalize: sigmoid(-score) → 0..1
            score = float(raw_scores[0])
            anomaly_score = 1.0 / (1.0 + np.exp(score))  # sigmoid(-x)

            return max(0.0, min(1.0, anomaly_score))

        except (TimeoutError, RuntimeError) as e:
            logger.warning(
                f"Anomaly scoring failed for signal {signal.id} ({e}), "
                f"using heuristic fallback"
            )
            return await self._heuristic_anomaly(signal)

    async def _heuristic_anomaly(self, signal: Signal) -> float:
        """Heuristic anomaly score when ONNX model isn't available.

        Based on content characteristics that indicate unusualness.
        """
        score = 0.5  # neutral default

        # Very short content is suspicious
        content_len = len(signal.raw_content or "")
        if content_len < 100:
            score += 0.2
        elif content_len > 10000:
            score += 0.1

        # Weekend signals in business domains are unusual
        if signal.fetched_at and signal.fetched_at.weekday() >= 5:
            score += 0.1

        # Late-night signals
        if signal.fetched_at and (
            signal.fetched_at.hour < 6 or signal.fetched_at.hour > 22
        ):
            score += 0.05

        return max(0.0, min(1.0, score))

    def _extract_anomaly_features(self, signal: Signal) -> np.ndarray:
        """Extract features for anomaly detection."""
        content_length = len(signal.raw_content or "")
        hour = signal.fetched_at.hour if signal.fetched_at else 12
        day_of_week = signal.fetched_at.weekday() if signal.fetched_at else 2

        # Get source type from contract relationship
        source_type_encoded = 0
        if hasattr(signal, "contract") and signal.contract:
            source_type_encoded = SOURCE_TYPE_MAP.get(signal.contract.source_type, 0)

        return np.array(
            [[content_length, hour, day_of_week, source_type_encoded]],
            dtype=np.float32,
        )

    # ── Trending Scoring ─────────────────────────────────────────────

    async def _score_trending(self, signal: Signal) -> float:
        """Score trending based on signal volume time-series slope.

        Computes the slope of daily signal counts over the past 7 days
        for signals of the same type. Higher slope = more trending.

        Falls back to heuristic scoring on timeout or error.
        """
        if not self.engine.is_model_available("trending_scorer"):
            return await self._heuristic_trending(signal)

        try:
            features = await self._extract_trending_features(signal)
            raw_scores = self.engine.predict("trending_scorer", features)

            # Normalize score to 0..1
            score = float(raw_scores[0])
            return max(0.0, min(1.0, score))

        except (TimeoutError, RuntimeError) as e:
            logger.warning(
                f"Trending scoring failed for signal {signal.id} ({e}), "
                f"using heuristic fallback"
            )
            return await self._heuristic_trending(signal)

    async def _heuristic_trending(self, signal: Signal) -> float:
        """Heuristic trending score: compare recent volume to baseline."""
        now = datetime.now(timezone.utc)

        # Count signals of same type in last 24h vs last 7d average
        recent_count = await self._count_signals_in_period(
            signal.signal_type,
            now - timedelta(hours=24),
            now,
        )

        week_count = await self._count_signals_in_period(
            signal.signal_type,
            now - timedelta(days=7),
            now,
        )

        daily_avg = week_count / 7.0 if week_count > 0 else 1.0

        if daily_avg == 0:
            return 0.5

        # Ratio of recent to average → trending score
        ratio = recent_count / daily_avg
        # Map ratio to 0..1: ratio=1 → 0.5, ratio≥3 → 1.0, ratio=0 → 0.0
        score = min(1.0, ratio / 3.0)
        return round(score, 4)

    async def _extract_trending_features(self, signal: Signal) -> np.ndarray:
        """Extract time-series features for trending prediction."""
        now = datetime.now(timezone.utc)
        daily_counts = []

        for days_ago in range(7):
            start = now - timedelta(days=days_ago + 1)
            end = now - timedelta(days=days_ago)
            count = await self._count_signals_in_period(signal.signal_type, start, end)
            daily_counts.append(count)

        # Reverse so index 0 = oldest
        daily_counts.reverse()

        # Features: 7 daily counts + slope + mean
        counts_arr = np.array(daily_counts, dtype=np.float32)
        if len(counts_arr) > 1:
            slope = np.polyfit(range(len(counts_arr)), counts_arr, 1)[0]
        else:
            slope = 0.0
        mean_count = float(counts_arr.mean())

        features = np.concatenate(
            [counts_arr, np.array([slope, mean_count], dtype=np.float32)]
        )
        return features.reshape(1, -1)

    async def _count_signals_in_period(
        self,
        signal_type: str,
        start: datetime,
        end: datetime,
    ) -> int:
        """Count signals of a given type in a time period."""
        result = await self.db.execute(
            select(func.count(Signal.id)).where(
                Signal.signal_type == signal_type,
                Signal.fetched_at >= start,
                Signal.fetched_at < end,
            )
        )
        return result.scalar_one()

    # ── Confidence Calibration ───────────────────────────────────────

    async def _score_confidence(self, signal: Signal) -> float:
        """Calibrate signal confidence using logistic regression.

        Features: [source_type, content_length, entity_match_count, freshness_hours]

        Falls back to heuristic scoring on timeout or error.
        """
        if not self.engine.is_model_available("confidence_calibrator"):
            return self._heuristic_confidence(signal)

        try:
            features = await self._extract_confidence_features(signal)
            probas = self.engine.predict_proba("confidence_calibrator", features)

            # Probability of "high quality" class
            if probas.ndim > 1 and probas.shape[1] > 1:
                score = float(probas[0][1])
            else:
                score = float(probas[0])

            return max(0.0, min(1.0, score))

        except (TimeoutError, RuntimeError) as e:
            logger.warning(
                f"Confidence scoring failed for signal {signal.id} ({e}), "
                f"using heuristic fallback"
            )
            return self._heuristic_confidence(signal)

    def _heuristic_confidence(self, signal: Signal) -> float:
        """Heuristic confidence when ONNX model isn't available.

        Combines content quality signals into a 0..1 score.
        """
        score = 0.5

        # Content length bonus
        content_len = len(signal.raw_content or "")
        if content_len > 500:
            score += 0.1
        if content_len > 2000:
            score += 0.1

        # Has title
        if signal.title:
            score += 0.1

        # Has summary
        if signal.summary:
            score += 0.1

        # Freshness (within 24h)
        if signal.published_at:
            hours_old = (
                datetime.now(timezone.utc) - signal.published_at
            ).total_seconds() / 3600
            if hours_old < 24:
                score += 0.1
            elif hours_old > 168:  # > 1 week
                score -= 0.1

        return max(0.0, min(1.0, score))

    async def _extract_confidence_features(self, signal: Signal) -> np.ndarray:
        """Extract features for confidence calibration."""
        # Source type encoding
        source_type_encoded = 0
        if hasattr(signal, "contract") and signal.contract:
            source_type_encoded = SOURCE_TYPE_MAP.get(signal.contract.source_type, 0)

        # Content length (log-scaled)
        content_length = len(signal.raw_content or "")

        # Entity match count
        entity_count = len(signal.entity_links) if signal.entity_links else 0

        # Freshness in hours
        freshness_hours = 48.0  # default
        if signal.published_at:
            freshness_hours = max(
                0.0,
                (datetime.now(timezone.utc) - signal.published_at).total_seconds()
                / 3600,
            )

        return np.array(
            [[source_type_encoded, content_length, entity_count, freshness_hours]],
            dtype=np.float32,
        )

    # ── Audit ────────────────────────────────────────────────────────

    async def _create_model_run(
        self,
        model_name: str,
        model_version: str,
        signals_count: int,
    ) -> MLModelRun:
        """Create an MLModelRun audit record."""
        return await self.run_repo.create(
            model_name=model_name,
            model_version=model_version,
            signals_processed=0,
            status="running",
            ran_at=datetime.now(timezone.utc),
        )
