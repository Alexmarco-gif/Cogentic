"""Train confidence calibrator (logistic regression) and export to ONNX.

Features: [source_type, content_length, entity_match_count, freshness_hours]
Output: Probability of signal being "high quality" (confidence 0..1)

Usage:
    python -m backend.ml.training.train_confidence

Retrains weekly via cron (RQ job).
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MODEL_NAME = "confidence_calibrator"
N_FEATURES = 4  # source_type, content_length, entity_match_count, freshness_hours


def train_confidence_model(
    features: np.ndarray | None = None,
    labels: np.ndarray | None = None,
    version: str | None = None,
    random_state: int = 42,
) -> Path:
    """Train logistic regression confidence calibrator and export to ONNX.

    Args:
        features: Training features [n_samples, 4]. Generates synthetic if None.
        labels: Binary labels (0=low, 1=high quality). Synthetic if None.
        version: Model version string. Auto-generated if None.
        random_state: Random seed.

    Returns:
        Path to the saved ONNX model file.
    """
    if version is None:
        version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

    if features is None or labels is None:
        logger.info("No training data provided, generating synthetic data")
        features, labels = _generate_synthetic_data(n_samples=1000)

    logger.info(
        f"Training {MODEL_NAME} {version}: "
        f"{features.shape[0]} samples, {N_FEATURES} features"
    )

    # Scale features for logistic regression
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # Train logistic regression
    model = LogisticRegression(
        random_state=random_state,
        max_iter=1000,
        C=1.0,
    )
    model.fit(features_scaled, labels)

    # Log training accuracy
    accuracy = model.score(features_scaled, labels)
    logger.info(f"Training accuracy: {accuracy:.4f}")

    # Export to ONNX (we export a pipeline with scaler + classifier)
    output_path = _export_to_onnx(model, scaler, version)

    logger.info(f"Model saved: {output_path}")
    return output_path


def _export_to_onnx(
    model: LogisticRegression,
    scaler: StandardScaler,
    version: str,
) -> Path:
    """Export sklearn pipeline to ONNX format."""
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    from sklearn.pipeline import Pipeline

    # Create pipeline
    pipeline = Pipeline(
        [
            ("scaler", scaler),
            ("classifier", model),
        ]
    )

    initial_type = [("float_input", FloatTensorType([None, N_FEATURES]))]

    onnx_model = convert_sklearn(
        pipeline,
        initial_types=initial_type,
        target_opset=15,
        options={id(model): {"zipmap": False}},  # Return array, not dict
    )

    models_dir = Path(settings.ml_models_dir)
    output_dir = models_dir / MODEL_NAME / version
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{MODEL_NAME}.onnx"

    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"ONNX model size: {size_mb:.2f}MB")

    return output_path


def _generate_synthetic_data(
    n_samples: int = 1000,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic training data for initial model bootstrap.

    Labels are generated heuristically:
    - Long content + API/RSS source + recent + entities → high quality
    """
    rng = np.random.default_rng(42)

    source_type = rng.integers(0, 4, size=n_samples).astype(np.float32)
    content_length = rng.lognormal(mean=7, sigma=1.5, size=n_samples).astype(np.float32)
    entity_count = rng.poisson(lam=2, size=n_samples).astype(np.float32)
    freshness_hours = rng.exponential(scale=48, size=n_samples).astype(np.float32)

    features = np.column_stack(
        [source_type, content_length, entity_count, freshness_hours]
    )

    # Heuristic labels
    quality_score = (
        (content_length > 500).astype(float) * 0.3
        + (entity_count > 0).astype(float) * 0.25
        + (freshness_hours < 48).astype(float) * 0.25
        + (source_type <= 1).astype(float) * 0.2  # API/RSS more reliable
    )
    labels = (quality_score >= 0.5).astype(np.int64)

    return features, labels


async def extract_training_features_from_db() -> tuple[np.ndarray, np.ndarray]:
    """Extract training features from existing signals in DB.

    Uses signal confidence > 0.7 as positive label, < 0.4 as negative.
    Signals with confidence between 0.4 and 0.7 are excluded.
    """
    from sqlalchemy import or_, select

    from backend.database import get_db_context
    from backend.models.signal import Signal

    source_type_map = {"api": 0, "rss": 1, "scraper": 2, "social": 3}
    now = datetime.now(timezone.utc)

    async with get_db_context() as db:
        result = await db.execute(
            select(Signal)
            .where(or_(Signal.confidence >= 0.7, Signal.confidence < 0.4))
            .limit(10000)
        )
        signals = result.scalars().all()

        if len(signals) < 50:
            return _generate_synthetic_data()

        features_list = []
        labels_list = []

        for s in signals:
            source = 0
            if hasattr(s, "contract") and s.contract:
                source = source_type_map.get(s.contract.source_type, 0)

            content_length = len(s.raw_content or "")
            entity_count = len(s.entity_links) if s.entity_links else 0
            freshness = (
                (now - s.fetched_at).total_seconds() / 3600 if s.fetched_at else 48.0
            )

            features_list.append([source, content_length, entity_count, freshness])
            labels_list.append(1 if s.confidence >= 0.7 else 0)

        return (
            np.array(features_list, dtype=np.float32),
            np.array(labels_list, dtype=np.int64),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = train_confidence_model()
    print(f"Confidence model saved to: {path}")
