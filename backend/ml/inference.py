"""ONNX Runtime inference engine.

Loads ONNX-exported models for fast (<100ms) inference.
Supports model version management (latest 3 versions hot).
Local filesystem in dev, Azure Blob in prod.
"""

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OnnxInferenceEngine:
    """ONNX Runtime inference engine with model version management.

    Features:
        - Loads models from local filesystem (dev) or Azure Blob (prod)
        - Keeps latest N model versions hot in memory
        - <100ms inference target per prediction
        - Thread-safe session management

    Model naming convention:
        {model_name}/v{version}/{model_name}.onnx
        e.g. anomaly_detector/v1/anomaly_detector.onnx
    """

    def __init__(self):
        self.models_dir = Path(settings.ml_models_dir)
        self.max_versions = settings.ml_model_max_versions
        self._sessions: dict[str, ort.InferenceSession] = {}
        self._model_metadata: dict[str, dict[str, Any]] = {}

        # Create models directory if it doesn't exist
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Session options for optimized inference
        self._session_options = ort.SessionOptions()
        self._session_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        self._session_options.intra_op_num_threads = 2
        self._session_options.inter_op_num_threads = 1

        # Health check: Validate required models on startup if enabled
        if settings.ml_validate_on_startup:
            self._validate_required_models()

    # ── Core Inference ───────────────────────────────────────────────

    def predict(
        self,
        model_name: str,
        features: np.ndarray,
        *,
        version: str | None = None,
    ) -> np.ndarray:
        """Run inference on an ONNX model with timeout guard.

        Args:
            model_name: Name of the model (e.g. 'anomaly_detector').
            features: Input feature array (2D: [n_samples, n_features]).
            version: Specific version to use. None = latest.

        Returns:
            Model output as numpy array.

        Raises:
            FileNotFoundError: If model file not found.
            RuntimeError: If inference fails or times out.
        """
        start = time.monotonic()

        session = self._get_session(model_name, version)
        input_name = session.get_inputs()[0].name

        # Ensure correct dtype (float32 for sklearn exports)
        if features.dtype != np.float32:
            features = features.astype(np.float32)

        # Ensure 2D
        if features.ndim == 1:
            features = features.reshape(1, -1)

        try:
            # Run inference with timeout guard
            outputs = self._run_with_timeout(session, input_name, features)
            result = outputs[0]
        except Exception as e:
            raise RuntimeError(f"Inference failed for {model_name}: {e}") from e

        elapsed_ms = (time.monotonic() - start) * 1000
        if elapsed_ms > settings.ml_inference_timeout_ms:
            logger.warning(
                f"Slow inference: {model_name} took {elapsed_ms:.1f}ms "
                f"(target: <{settings.ml_inference_timeout_ms}ms)"
            )
        else:
            logger.debug(f"Inference {model_name}: {elapsed_ms:.1f}ms")

        return result

    def predict_proba(
        self,
        model_name: str,
        features: np.ndarray,
        *,
        version: str | None = None,
    ) -> np.ndarray:
        """Run inference and return probability outputs.

        For classifiers that output probabilities (e.g. logistic regression).

        Args:
            model_name: Name of the model.
            features: Input feature array.
            version: Specific version to use.

        Returns:
            Probability array.
        """
        start = time.monotonic()

        session = self._get_session(model_name, version)
        input_name = session.get_inputs()[0].name

        if features.dtype != np.float32:
            features = features.astype(np.float32)
        if features.ndim == 1:
            features = features.reshape(1, -1)

        try:
            outputs = session.run(None, {input_name: features})
            # Second output is typically probabilities for classifiers
            if len(outputs) > 1:
                return outputs[1]
            return outputs[0]
        except Exception as e:
            raise RuntimeError(
                f"Probability inference failed for {model_name}: {e}"
            ) from e

    # ── Model Management ─────────────────────────────────────────────

    def load_model(self, model_name: str, version: str | None = None) -> bool:
        """Pre-load a model into memory.

        Args:
            model_name: Model name.
            version: Version string. None = latest available.

        Returns:
            True if loaded successfully.
        """
        try:
            self._get_session(model_name, version)
            return True
        except FileNotFoundError:
            return False

    def is_model_available(self, model_name: str, version: str | None = None) -> bool:
        """Check if a model file exists (without loading it)."""
        try:
            self._resolve_model_path(model_name, version)
            return True
        except FileNotFoundError:
            return False

    def get_loaded_models(self) -> list[str]:
        """Get list of currently loaded model session keys."""
        return list(self._sessions.keys())

    def get_available_versions(self, model_name: str) -> list[str]:
        """List available versions for a model (sorted descending)."""
        model_dir = self.models_dir / model_name
        if not model_dir.exists():
            return []

        versions = []
        for d in model_dir.iterdir():
            if d.is_dir() and d.name.startswith("v"):
                onnx_file = d / f"{model_name}.onnx"
                if onnx_file.exists():
                    versions.append(d.name)

        return sorted(versions, reverse=True)

    def unload_model(self, model_name: str, version: str | None = None):
        """Remove a model session from memory."""
        if version:
            key = f"{model_name}:{version}"
        else:
            key = f"{model_name}:latest"

        if key in self._sessions:
            del self._sessions[key]
            logger.info(f"Unloaded model: {key}")

    def cleanup_old_versions(self, model_name: str):
        """Keep only the latest N versions, remove older ones from memory."""
        versions = self.get_available_versions(model_name)
        if len(versions) <= self.max_versions:
            return

        old_versions = versions[self.max_versions :]
        for v in old_versions:
            self.unload_model(model_name, v)
            logger.info(f"Cleaned up old version: {model_name}/{v}")

    # ── Internal ─────────────────────────────────────────────────────
    def _run_with_timeout(
        self,
        session: ort.InferenceSession,
        input_name: str,
        features: np.ndarray,
    ) -> list:
        """Run ONNX inference with timeout guard.

        Args:
            session: Active ONNX session.
            input_name: Name of input tensor.
            features: Input feature array.

        Returns:
            Model outputs.

        Raises:
            TimeoutError: If inference exceeds timeout.
            RuntimeError: If inference fails.
        """
        import concurrent.futures

        timeout_sec = settings.ml_inference_timeout_ms / 1000.0

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(session.run, None, {input_name: features})
            try:
                return future.result(timeout=timeout_sec)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"Inference exceeded {settings.ml_inference_timeout_ms}ms timeout"
                )

    def _validate_required_models(self) -> None:
        """Validate that all required models are loadable.

        Checks models listed in settings.ml_models_required.
        Raises exception on first missing/corrupt model.

        Raises:
            FileNotFoundError: If required model not found.
            RuntimeError: If model loading fails.
        """
        logger.info(
            f"Validating {len(settings.ml_models_required)} required ML models..."
        )

        for model_name in settings.ml_models_required:
            try:
                session = self._get_session(model_name, version=None)
                logger.info(f"✓ Model '{model_name}' validated")
            except FileNotFoundError as e:
                logger.error(f"✗ Required model '{model_name}' not found: {e}")
                raise
            except Exception as e:
                logger.error(f"✗ Required model '{model_name}' failed to load: {e}")
                raise RuntimeError(
                    f"Required model '{model_name}' validation failed: {e}"
                ) from e

        logger.info("All required ML models validated successfully")

    def _get_session(
        self,
        model_name: str,
        version: str | None = None,
    ) -> ort.InferenceSession:
        """Get or create an ONNX Runtime session for a model."""
        if version:
            key = f"{model_name}:{version}"
        else:
            key = f"{model_name}:latest"

        if key in self._sessions:
            return self._sessions[key]

        model_path = self._resolve_model_path(model_name, version)

        logger.info(f"Loading ONNX model: {model_path}")
        session = ort.InferenceSession(
            str(model_path),
            self._session_options,
            providers=["CPUExecutionProvider"],
        )

        self._sessions[key] = session

        # Store metadata
        self._model_metadata[key] = {
            "path": str(model_path),
            "inputs": [
                {"name": i.name, "shape": i.shape, "type": i.type}
                for i in session.get_inputs()
            ],
            "outputs": [
                {"name": o.name, "shape": o.shape, "type": o.type}
                for o in session.get_outputs()
            ],
        }

        return session

    def _resolve_model_path(
        self,
        model_name: str,
        version: str | None = None,
    ) -> Path:
        """Resolve the filesystem path to a model's ONNX file.

        If no version specified, uses the latest available.

        Raises:
            FileNotFoundError: If no model file found.
        """
        model_dir = self.models_dir / model_name

        if version:
            model_path = model_dir / version / f"{model_name}.onnx"
            if not model_path.exists():
                raise FileNotFoundError(f"Model not found: {model_path}")
            return model_path

        # Find latest version
        versions = self.get_available_versions(model_name)
        if not versions:
            raise FileNotFoundError(
                f"No versions found for model: {model_name} " f"(searched: {model_dir})"
            )

        latest = versions[0]
        return model_dir / latest / f"{model_name}.onnx"


# Singleton engine instance
_engine: OnnxInferenceEngine | None = None


def get_inference_engine() -> OnnxInferenceEngine:
    """Get or create the singleton inference engine."""
    global _engine
    if _engine is None:
        _engine = OnnxInferenceEngine()
    return _engine
