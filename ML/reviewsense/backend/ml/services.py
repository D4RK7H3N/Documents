"""Inference service for the ReviewSense sentiment model.

The trained model artifact is loaded into process memory exactly once
(either at Django startup via MlConfig.ready(), or lazily on the first
inference), and every request reuses that single in-memory instance.

Views must call predict() / load_model() from this module and must never
load the artifact themselves.
"""
import logging
import threading
import time
from pathlib import Path

import joblib

from django.conf import settings

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(settings.BASE_DIR) / "ml" / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "model.joblib"

_bundle = None
_lock = threading.Lock()


class ModelNotReadyError(RuntimeError):
    """Raised when inference is requested before the model has been trained."""


def load_model():
    """Load the model artifact into memory once (idempotent, thread-safe)."""
    global _bundle
    if _bundle is not None:
        return _bundle
    with _lock:
        if _bundle is not None:
            return _bundle
        if not MODEL_PATH.exists():
            logger.warning(
                "Model artifact not found at %s. Run `python manage.py train_model` first.",
                MODEL_PATH,
            )
            return None
        _bundle = joblib.load(MODEL_PATH)
        logger.info("ML model '%s' loaded from %s", _bundle.get("version"), MODEL_PATH)
        return _bundle


def is_model_ready() -> bool:
    return _bundle is not None


def predict(text: str) -> dict:
    """Classify one review string.

    Returns a dict with: prediction (label), confidence (max class
    probability), model_version and inference_ms.
    """
    bundle = load_model()
    if bundle is None:
        raise ModelNotReadyError(
            "Model is not trained yet. Run `python manage.py train_model` first."
        )

    pipeline = bundle["pipeline"]
    started = time.perf_counter()
    probabilities = pipeline.predict_proba([text])[0]
    elapsed_ms = (time.perf_counter() - started) * 1000

    best_index = int(probabilities.argmax())
    return {
        "prediction": bundle["labels"][best_index],
        "confidence": round(float(probabilities[best_index]), 4),
        "model_version": bundle.get("version", "unknown"),
        "inference_ms": round(elapsed_ms, 2),
    }
