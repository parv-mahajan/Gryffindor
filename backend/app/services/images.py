"""Optional zero-shot image classification with CLIP.

Disabled by default (CIVICSENSE_CLIP_ENABLED=0). When the weights are not
available the pipeline degrades gracefully to text-only scoring and reports
image_score = null instead of failing the request.
"""

from __future__ import annotations

import threading

from .. import config, settings

_model = None
_processor = None
_lock = threading.Lock()
_failed = False


def available() -> bool:
    return config.CLIP_ENABLED


def _load():
    """Load CLIP lazily. Returns (model, processor) or None when unavailable."""
    global _model, _processor, _failed
    if not config.CLIP_ENABLED:
        return None
    if _model is not None:
        return _model, _processor
    if _failed:
        return None
    with _lock:
        if _model is None and not _failed:
            try:
                from transformers import CLIPModel, CLIPProcessor

                model = CLIPModel.from_pretrained(config.CLIP_MODEL)
                processor = CLIPProcessor.from_pretrained(config.CLIP_MODEL)
                model.eval()
                _model, _processor = model, processor
            except Exception as exc:  # network missing, weights missing, ...
                _failed = True
                print(f"[images] CLIP unavailable, continuing without image scores: {exc}")
                return None
    return _model, _processor


def classify_image(path) -> dict | None:
    """Zero-shot classify one image. Returns None when CLIP is off/unavailable."""
    loaded = _load()
    if loaded is None:
        return None
    model, processor = loaded

    import torch
    from PIL import Image

    try:
        image = Image.open(path).convert("RGB")
    except Exception:
        return None

    prompts = []
    for category in settings.CATEGORIES:
        for prototype in category["prototypes"][:2]:
            prompts.append((category["key"], prototype))
    labels = [p for p, _ in prompts]
    texts = [t for _, t in prompts]

    inputs = processor(text=texts, images=image, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = outputs.logits_per_image.softmax(dim=1)[0]

    scores: dict[str, float] = {}
    for label, prob in zip(labels, probs.tolist()):
        scores[label] = max(scores.get(label, 0.0), prob)

    best = max(scores, key=lambda k: scores[k])
    return {
        "category": best,
        "confidence": round(scores[best], 4),
        "scores": {k: round(v, 4) for k, v in scores.items()},
    }
