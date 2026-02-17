"""Refinement and ML training RQ job handlers.

Entry points for RQ workers. Sync functions that wrap async services.
Enqueued after signal acquisition or by weekly cron (training).
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ── Refinement Jobs ──────────────────────────────────────────────────


def refine_signals(signal_ids: list[str]) -> dict[str, Any]:
    """Refine a batch of signals (embedding + entity + ML scoring).

    Called after acquisition pipeline stores new signals.

    Args:
        signal_ids: List of signal UUID strings.

    Returns:
        Refinement summary dict.
    """
    logger.info(f"Starting refinement job for {len(signal_ids)} signals")
    start = datetime.now(timezone.utc)

    from backend.services.refinement_service import run_refine_batch

    result = run_refine_batch(signal_ids)

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    result["duration_seconds"] = round(duration, 2)
    logger.info(f"Refinement completed in {duration:.1f}s: {result}")
    return result


def refine_unprocessed(limit: int = 100) -> dict[str, Any]:
    """Catch-up refinement for signals missing embeddings.

    Called periodically or manually to process backlog.

    Args:
        limit: Maximum signals to process.

    Returns:
        Refinement summary dict.
    """
    logger.info(f"Starting unprocessed refinement job (limit={limit})")
    start = datetime.now(timezone.utc)

    from backend.services.refinement_service import run_refine_unprocessed

    result = run_refine_unprocessed(limit=limit)

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    result["duration_seconds"] = round(duration, 2)
    logger.info(f"Unprocessed refinement completed in {duration:.1f}s: {result}")
    return result


# ── ML Training Jobs ─────────────────────────────────────────────────


def train_all_models() -> dict[str, Any]:
    """Train all 3 ML models and export to ONNX.

    Called weekly by cron (RQ job).
    Trains with synthetic data initially, then DB data when available.

    Returns:
        Training summary dict.
    """
    logger.info("Starting weekly model training job")
    start = datetime.now(timezone.utc)
    results = {}

    # 1. Train anomaly detector
    try:
        from backend.ml.training.train_anomaly import train_anomaly_model

        path = train_anomaly_model()
        results["anomaly_detector"] = {"status": "trained", "path": str(path)}
    except Exception as e:
        logger.error(f"Anomaly training failed: {e}")
        results["anomaly_detector"] = {"status": "failed", "error": str(e)}

    # 2. Train trending scorer
    try:
        from backend.ml.training.train_trending import train_trending_model

        path = train_trending_model()
        results["trending_scorer"] = {"status": "trained", "path": str(path)}
    except Exception as e:
        logger.error(f"Trending training failed: {e}")
        results["trending_scorer"] = {"status": "failed", "error": str(e)}

    # 3. Train confidence calibrator
    try:
        from backend.ml.training.train_confidence import train_confidence_model

        path = train_confidence_model()
        results["confidence_calibrator"] = {"status": "trained", "path": str(path)}
    except Exception as e:
        logger.error(f"Confidence training failed: {e}")
        results["confidence_calibrator"] = {"status": "failed", "error": str(e)}

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"Model training completed in {duration:.1f}s: {results}")

    return {
        "models": results,
        "duration_seconds": round(duration, 2),
    }


def train_single_model(model_name: str) -> dict[str, Any]:
    """Train a specific model by name.

    Args:
        model_name: One of 'anomaly_detector', 'trending_scorer', 'confidence_calibrator'

    Returns:
        Training result dict.
    """
    logger.info(f"Training model: {model_name}")

    trainers = {
        "anomaly_detector": "backend.ml.training.train_anomaly",
        "trending_scorer": "backend.ml.training.train_trending",
        "confidence_calibrator": "backend.ml.training.train_confidence",
    }

    if model_name not in trainers:
        return {"status": "error", "message": f"Unknown model: {model_name}"}

    try:
        import importlib

        module = importlib.import_module(trainers[model_name])
        func_name = f"train_{model_name.split('_')[0]}_model"
        train_func = getattr(module, func_name)
        path = train_func()
        return {"status": "trained", "model": model_name, "path": str(path)}
    except Exception as e:
        logger.error(f"Training {model_name} failed: {e}")
        return {"status": "failed", "model": model_name, "error": str(e)}
