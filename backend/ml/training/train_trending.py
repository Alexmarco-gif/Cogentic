"""Train trending scorer and export to ONNX.

Features: [day1_count, day2_count, ..., day7_count, slope, mean_count] (9 features)
Output: Trending score (0..1)

Uses linear regression on daily signal counts. Higher slope = more trending.
Trained as a regressor on computed trending labels.

Usage:
    python -m backend.ml.training.train_trending

Retrains weekly via cron (RQ job).
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MODEL_NAME = "trending_scorer"
N_FEATURES = 9  # 7 daily counts + slope + mean


def train_trending_model(
    features: np.ndarray | None = None,
    labels: np.ndarray | None = None,
    version: str | None = None,
    random_state: int = 42,
) -> Path:
    """Train trending scorer (Ridge regression) and export to ONNX.

    Args:
        features: Training features [n_samples, 9]. Synthetic if None.
        labels: Trending scores 0..1. Synthetic if None.
        version: Model version string. Auto-generated if None.
        random_state: Random seed.

    Returns:
        Path to the saved ONNX model file.
    """
    if version is None:
        version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

    if features is None or labels is None:
        logger.info("No training data provided, generating synthetic data")
        features, labels = _generate_synthetic_data(n_samples=500)

    logger.info(
        f"Training {MODEL_NAME} {version}: "
        f"{features.shape[0]} samples, {N_FEATURES} features"
    )

    # Scale features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # Train Ridge regression (bounded output via clipping post-inference)
    model = Ridge(alpha=1.0, random_state=random_state)
    model.fit(features_scaled, labels)

    # Log training R²
    r2 = model.score(features_scaled, labels)
    logger.info(f"Training R² score: {r2:.4f}")

    output_path = _export_to_onnx(model, scaler, version)
    logger.info(f"Model saved: {output_path}")
    return output_path


def _export_to_onnx(
    model: Ridge,
    scaler: StandardScaler,
    version: str,
) -> Path:
    """Export sklearn pipeline to ONNX format."""
    from sklearn.pipeline import Pipeline
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType

    pipeline = Pipeline([
        ("scaler", scaler),
        ("regressor", model),
    ])

    initial_type = [("float_input", FloatTensorType([None, N_FEATURES]))]

    onnx_model = convert_sklearn(
        pipeline,
        initial_types=initial_type,
        target_opset=15,
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
    n_samples: int = 500,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic time-series training data.

    Simulates various trending patterns:
    - Flat (not trending)
    - Upward slope (trending)
    - Spike patterns
    """
    rng = np.random.default_rng(42)
    features_list = []
    labels_list = []

    for _ in range(n_samples):
        pattern = rng.choice(["flat", "trending_up", "trending_down", "spike"])

        if pattern == "flat":
            base = rng.integers(5, 50)
            counts = rng.poisson(lam=base, size=7).astype(np.float32)
            label = 0.3 + rng.random() * 0.2  # 0.3-0.5

        elif pattern == "trending_up":
            base = rng.integers(5, 30)
            growth = rng.uniform(0.2, 0.8)
            counts = np.array(
                [rng.poisson(base * (1 + growth * i)) for i in range(7)],
                dtype=np.float32,
            )
            label = 0.7 + rng.random() * 0.3  # 0.7-1.0

        elif pattern == "trending_down":
            base = rng.integers(20, 60)
            decay = rng.uniform(0.1, 0.5)
            counts = np.array(
                [rng.poisson(max(1, base * (1 - decay * i))) for i in range(7)],
                dtype=np.float32,
            )
            label = 0.1 + rng.random() * 0.2  # 0.1-0.3

        else:  # spike
            base = rng.integers(5, 20)
            spike_day = rng.integers(4, 7)
            counts = rng.poisson(lam=base, size=7).astype(np.float32)
            counts[spike_day] = base * rng.integers(3, 8)
            label = 0.6 + rng.random() * 0.3  # 0.6-0.9

        # Compute slope and mean
        slope = np.polyfit(range(7), counts, 1)[0]
        mean_count = float(counts.mean())

        feature_row = np.concatenate(
            [counts, np.array([slope, mean_count], dtype=np.float32)]
        )
        features_list.append(feature_row)
        labels_list.append(label)

    return (
        np.array(features_list, dtype=np.float32),
        np.array(labels_list, dtype=np.float32),
    )


async def extract_training_features_from_db() -> tuple[np.ndarray, np.ndarray]:
    """Extract trending features from existing signals in DB.

    For each signal type, compute 7-day daily counts at multiple offsets
    and derive trending labels from the slope.
    """
    from sqlalchemy import func, select

    from backend.database import get_db_context
    from backend.models.signal import Signal

    now = datetime.now(timezone.utc)

    async with get_db_context() as db:
        # Get distinct signal types
        result = await db.execute(
            select(Signal.signal_type).distinct()
        )
        signal_types = [row[0] for row in result.all()]

        if not signal_types:
            return _generate_synthetic_data()

        features_list = []
        labels_list = []

        for sig_type in signal_types:
            # Generate multiple training samples by sliding the 7-day window
            for offset in range(0, 28, 7):
                daily_counts = []
                for day in range(7):
                    start = now - timedelta(days=offset + day + 1)
                    end = now - timedelta(days=offset + day)
                    count_result = await db.execute(
                        select(func.count(Signal.id)).where(
                            Signal.signal_type == sig_type,
                            Signal.fetched_at >= start,
                            Signal.fetched_at < end,
                        )
                    )
                    daily_counts.append(float(count_result.scalar_one()))

                daily_counts.reverse()
                counts_arr = np.array(daily_counts, dtype=np.float32)

                if counts_arr.sum() == 0:
                    continue

                slope = np.polyfit(range(7), counts_arr, 1)[0]
                mean_count = float(counts_arr.mean())

                features = np.concatenate(
                    [counts_arr, np.array([slope, mean_count], dtype=np.float32)]
                )
                features_list.append(features)

                # Label: normalize slope relative to mean
                if mean_count > 0:
                    normalized_slope = slope / mean_count
                    label = min(1.0, max(0.0, 0.5 + normalized_slope * 2))
                else:
                    label = 0.5
                labels_list.append(label)

        if len(features_list) < 20:
            return _generate_synthetic_data()

        return (
            np.array(features_list, dtype=np.float32),
            np.array(labels_list, dtype=np.float32),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = train_trending_model()
    print(f"Trending model saved to: {path}")
