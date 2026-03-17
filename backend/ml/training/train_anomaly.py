"""Train Isolation Forest anomaly detector and export to ONNX.

Features: [content_length, hour_of_day, day_of_week, source_type_encoded]
Output: Anomaly decision scores (negative = anomalous)

Usage:
    python -m backend.ml.training.train_anomaly

Retrains weekly via cron (RQ job).
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MODEL_NAME = "anomaly_detector"
N_FEATURES = 4  # content_length, hour, day_of_week, source_type


def train_anomaly_model(
    features: np.ndarray | None = None,
    version: str | None = None,
    contamination: float = 0.1,
    n_estimators: int = 100,
    random_state: int = 42,
) -> Path:
    """Train Isolation Forest and export to ONNX.

    Args:
        features: Training feature array [n_samples, 4]. If None, uses synthetic data.
        version: Model version string. Auto-generated if None.
        contamination: Expected proportion of anomalies.
        n_estimators: Number of trees.
        random_state: Random seed for reproducibility.

    Returns:
        Path to the saved ONNX model file.
    """
    if version is None:
        version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

    # Use synthetic data if no real training data provided
    if features is None:
        logger.info("No training data provided, generating synthetic data")
        features = _generate_synthetic_data(n_samples=1000)

    logger.info(
        f"Training {MODEL_NAME} {version}: "
        f"{features.shape[0]} samples, {N_FEATURES} features, "
        f"contamination={contamination}"
    )

    # Train Isolation Forest
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(features)

    # Export model (joblib — IsolationForest ONNX conversion is broken)
    output_path = _export_model(model, version, features)

    logger.info(f"Model saved: {output_path}")
    return output_path


def _export_model(
    model: IsolationForest,
    version: str,
    sample_data: np.ndarray,
) -> Path:
    """Export IsolationForest model using joblib serialization.

    Note: IsolationForest ONNX conversion is broken in skl2onnx 1.20+
    due to a recursion bug in the identity-node optimisation pass.
    joblib is used instead — the inference engine supports both formats.
    """
    import joblib

    # Save to versioned directory
    models_dir = Path(settings.ml_models_dir)
    output_dir = models_dir / MODEL_NAME / version
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{MODEL_NAME}.joblib"

    joblib.dump(model, output_path)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Joblib model size: {size_mb:.2f}MB")
    if size_mb > 100:
        logger.warning(f"Model exceeds 100MB limit: {size_mb:.2f}MB")

    return output_path


def _generate_synthetic_data(n_samples: int = 1000) -> np.ndarray:
    """Generate synthetic training data for initial model bootstrap.

    Features: [content_length, hour_of_day, day_of_week, source_type]
    """
    rng = np.random.default_rng(42)

    content_length = rng.lognormal(mean=7, sigma=1.5, size=n_samples).astype(np.float32)
    hour_of_day = rng.integers(0, 24, size=n_samples).astype(np.float32)
    day_of_week = rng.integers(0, 7, size=n_samples).astype(np.float32)
    source_type = rng.integers(0, 4, size=n_samples).astype(np.float32)

    return np.column_stack([content_length, hour_of_day, day_of_week, source_type])


async def extract_training_features_from_db() -> np.ndarray:
    """Extract training features from existing signals in DB.

    Used by the weekly retrain cron job.
    """
    from sqlalchemy import select

    from backend.database import get_db_context
    from backend.models.signal import Signal

    source_type_map = {"api": 0, "rss": 1, "scraper": 2, "social": 3}

    async with get_db_context() as db:
        result = await db.execute(
            select(Signal).where(Signal.raw_content.is_not(None)).limit(10000)
        )
        signals = result.scalars().all()

        if not signals:
            return _generate_synthetic_data()

        features = []
        for s in signals:
            content_length = len(s.raw_content or "")
            hour = s.fetched_at.hour if s.fetched_at else 12
            day = s.fetched_at.weekday() if s.fetched_at else 2
            source = 0
            if hasattr(s, "contract") and s.contract:
                source = source_type_map.get(s.contract.source_type, 0)
            features.append([content_length, hour, day, source])

        return np.array(features, dtype=np.float32)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = train_anomaly_model()
    print(f"Anomaly model saved to: {path}")
