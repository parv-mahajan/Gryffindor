"""Sentence embedding service (all-MiniLM-L6-v2).

The model is loaded lazily on first use and kept warm for the life of the
process, so a request only pays the ~10 ms encode cost.
"""

from __future__ import annotations

import threading

import numpy as np

from .. import config

_model = None
_lock = threading.Lock()


def get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def encode(texts: list[str]) -> np.ndarray:
    """Return L2-normalised embeddings, shape (n, EMBEDDING_DIM)."""
    if not texts:
        return np.zeros((0, config.EMBEDDING_DIM), dtype=np.float32)
    vectors = get_model().encode(
        texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
    )
    return vectors.astype(np.float32)


def encode_one(text: str) -> list[float]:
    return encode([text])[0].tolist()


def cosine(a: np.ndarray | list[float], b: np.ndarray | list[float]) -> float:
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    if va.size == 0 or vb.size == 0:
        return 0.0
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
