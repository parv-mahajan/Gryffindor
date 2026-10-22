"""Hybrid category classifier.

Two signals are combined:

* an embedding signal - cosine similarity between the complaint embedding and
  the prototype phrases of every category, turned into a distribution with a
  softmax so the numbers behave like confidences;
* a rule signal - a small keyword layer that fires on obvious wording
  ("manhole", "no light", ...).

An optional CLIP zero-shot image score can be fused on top.
"""

from __future__ import annotations

import re
import threading

import numpy as np

from .. import config, settings
from . import embeddings, images

_PROTOTYPE_CACHE: dict[str, tuple[np.ndarray, list[str]]] = {}
_lock = threading.Lock()

# How much the keyword rule layer is allowed to move the score.
KEYWORD_BLEND = settings.KEYWORD_BLEND
# Share of the image score in the fused confidence.
IMAGE_WEIGHT = 0.25
# Softmax temperature applied to cosine similarities.
TEMPERATURE = 0.055

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "at",
    "on", "in", "of", "to", "for", "with", "near", "and", "or", "but", "it",
    "its", "this", "that", "there", "here", "has", "have", "had", "not", "no",
    "please", "kindly", "some", "still", "same", "before", "after", "from",
    "by", "so", "very", "much", "also", "just", "now", "they", "we", "i",
    "you", "my", "our", "their", "his", "her", "them", "me", "us", "about",
    "over", "under", "into", "out", "up", "down", "one", "two", "any",
}


def _content_words(text: str) -> int:
    tokens = [t for t in re.findall(r"[a-z0-9']+", text.lower()) if len(t) > 2]
    return sum(1 for t in tokens if t not in STOPWORDS)


def _prototype_matrix() -> dict[str, tuple[np.ndarray, list[str]]]:
    """Embed every category prototype phrase once and cache it."""
    if _PROTOTYPE_CACHE:
        return _PROTOTYPE_CACHE
    with _lock:
        if _PROTOTYPE_CACHE:
            return _PROTOTYPE_CACHE
        for category in settings.CATEGORIES:
            phrases = category["prototypes"]
            matrix = embeddings.encode(phrases)
            _PROTOTYPE_CACHE[category["key"]] = (matrix, phrases)
        return _PROTOTYPE_CACHE


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _same(token: str, keyword_token: str) -> bool:
    if token == keyword_token:
        return True
    if token == keyword_token + "s":
        return True
    if token == keyword_token + "es":
        return True
    return False


def _matches(tokens: list[str], keyword: list[str], slack: int = 4) -> bool:
    """Match a keyword phrase, allowing a few filler words in between.

    "lights are off" then matches "all the lights near the gate are off".
    """
    n = len(keyword)
    if n == 1:
        return any(_same(t, keyword[0]) for t in tokens)
    for i in range(len(tokens)):
        if not _same(tokens[i], keyword[0]):
            continue
        matched = 1
        skipped = 0
        pos = i + 1
        while matched < n and pos < len(tokens):
            if _same(tokens[pos], keyword[matched]):
                matched += 1
            else:
                skipped += 1
                if skipped > slack:
                    break
            pos += 1
        if matched == n:
            return True
    return False


def _keyword_evidence(matched: list[str]) -> int:
    """Strength of the rule evidence for one category.

    Every matched phrase counts for its own length plus a bonus for being an
    extra independent hit, so a report that says "choked drain" (two tokens,
    two phrases) outweighs one that only says "waterlogging" (one token).
    """
    return sum(len(_tokenize(phrase)) + 2 for phrase in matched)


def _keyword_hits(text: str) -> dict[str, list[str]]:
    tokens = _tokenize(text)
    hits: dict[str, list[str]] = {}
    for category in settings.CATEGORIES:
        matched = [
            phrase
            for phrase in category["keywords"]
            if _matches(tokens, _tokenize(phrase))
        ]
        if matched:
            matched.sort(key=len, reverse=True)
            hits[category["key"]] = matched
    return hits


def _similarities(vector: np.ndarray) -> dict[str, tuple[float, str]]:
    """Best prototype cosine per category plus the phrase that produced it."""
    cache = _prototype_matrix()
    out: dict[str, tuple[float, str]] = {}
    for key, (matrix, phrases) in cache.items():
        sims = matrix @ vector
        best = int(np.argmax(sims))
        out[key] = (float(sims[best]), phrases[best])
    return out


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    keys = list(scores)
    values = np.array([scores[k] for k in keys], dtype=np.float64) / TEMPERATURE
    values -= values.max()
    exp = np.exp(values)
    probs = exp / exp.sum()
    return {k: float(p) for k, p in zip(keys, probs)}


def classify(description: str, photo_paths: list[str] | None = None) -> dict:
    """Classify a complaint and explain the decision."""
    text = (description or "").strip()
    lowered = text.lower()

    vector = embeddings.encode([text])[0]
    sims = _similarities(vector)
    raw_softmax = _softmax({k: v[0] for k, v in sims.items()})

    # Absolute gate: how well does this text match the closest prototype at
    # all? A report that matches nothing well cannot be classified with
    # confidence, however clear the relative ranking looks.
    top_sim = max(v[0] for v in sims.values())
    absolute = np.clip(
        (top_sim - settings.ABSOLUTE_GATE_LOW) / settings.ABSOLUTE_GATE_SPAN, 0.0, 1.0
    )
    # Specificity: short one-liners carry too little information.
    specificity = min(1.0, _content_words(lowered) / settings.SPECIFICITY_CONTENT_WORDS)
    embedding_conf = {k: v * absolute * specificity for k, v in raw_softmax.items()}

    hits = _keyword_hits(lowered)
    # The rule layer is only trusted as far as the strongest evidence it found.
    # A category with a weaker rule hit keeps a proportionally smaller share of
    # the keyword confidence, so "choked drain ... waterlogging" is routed to
    # drainage instead of being decided by the embedding alone.
    evidence = {key: _keyword_evidence(matched) for key, matched in hits.items()}
    top_evidence = max(evidence.values(), default=0)
    keyword_conf = {
        key: (
            settings.KEYWORD_CONFIDENCE * evidence[key] / top_evidence
            if top_evidence and key in evidence
            else 0.0
        )
        for key in embedding_conf
    }

    fused: dict[str, float] = {}
    for key in embedding_conf:
        blended = (1 - KEYWORD_BLEND) * embedding_conf[key] + KEYWORD_BLEND * keyword_conf[key]
        fused[key] = min(1.0, blended)

    image_result = None
    if photo_paths:
        for path in photo_paths:
            image_result = images.classify_image(path)
            if image_result:
                break

    image_scores = None
    if image_result:
        image_conf = image_result["confidence"]
        image_key = image_result["category"]
        adjusted = dict(fused)
        if image_key in adjusted:
            adjusted[image_key] = min(
                1.0, (1 - IMAGE_WEIGHT) * adjusted[image_key] + IMAGE_WEIGHT * image_conf
            )
        image_scores = {
            "text_confidence": round(max(fused.values()), 4),
            "image_confidence": round(image_conf, 4),
            "image_category": image_key,
            "image_scores": image_result["scores"],
            "fused_confidence": round(max(adjusted.values()), 4),
            "fused_category": max(adjusted, key=lambda k: adjusted[k]),
            "weight": IMAGE_WEIGHT,
        }
        fused = adjusted

    ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
    top_key, top_conf = ranked[0]
    second_conf = ranked[1][1] if len(ranked) > 1 else 0.0
    gap = top_conf - second_conf

    review_reasons: list[str] = []
    if top_conf < settings.REVIEW_MIN_CONFIDENCE:
        review_reasons.append(
            f"top confidence {top_conf:.2f} is below {settings.REVIEW_MIN_CONFIDENCE:.2f}"
        )
    if gap < settings.REVIEW_MIN_TOP_GAP:
        review_reasons.append(
            f"top1/top2 gap {gap:.2f} is below {settings.REVIEW_MIN_TOP_GAP:.2f}"
        )
    needs_review = bool(review_reasons)

    alternatives = []
    for key, conf in ranked[:3]:
        category = settings.CATEGORY_BY_KEY[key]
        best_sim, best_phrase = sims[key]
        alternatives.append(
            {
                "key": key,
                "name": category["name"],
                "confidence": round(conf, 4),
                "explanation": _explain(key, hits.get(key, []), best_phrase, best_sim, conf),
            }
        )

    best_sim, best_phrase = sims[top_key]
    explanation = {
        "method": "embedding+keywords" + ("+clip" if image_result else ""),
        "summary": _summary(top_key, top_conf, hits.get(top_key, []), best_phrase, best_sim),
        "matched_keywords": hits.get(top_key, []),
        "keyword_evidence": evidence.get(top_key, 0),
        "keyword_confidence": round(keyword_conf[top_key], 4),
        "embedding_confidence": round(embedding_conf[top_key], 4),
        "nearest_prototype": best_phrase,
        "prototype_similarity": round(best_sim, 4),
        "absolute_gate": round(float(absolute), 4),
        "specificity": round(specificity, 4),
        "content_words": _content_words(lowered),
        "temperature": TEMPERATURE,
        "keyword_blend": KEYWORD_BLEND,
        "top1_top2_gap": round(gap, 4),
        "review_reason": "; ".join(review_reasons) if review_reasons else None,
        "image_confidence": round(image_result["confidence"], 4) if image_result else None,
        "image_category": image_result["category"] if image_result else None,
    }

    return {
        "category": top_key,
        "category_name": settings.CATEGORY_BY_KEY[top_key]["name"],
        "confidence": round(top_conf, 4),
        "alternatives": alternatives,
        "needs_review": needs_review,
        "explanation": explanation,
        "image_scores": image_scores,
        "model_version": config.MODEL_VERSION,
        # The sentence embedding is handed back so the caller can store it for
        # later duplicate comparisons instead of encoding the text twice.
        "embedding": vector.tolist(),
    }


def _explain(key: str, matched: list[str], phrase: str, similarity: float, confidence: float) -> str:
    bits = []
    if matched:
        bits.append(f"matched keywords: {', '.join(matched[:4])}")
    bits.append(f"nearest prototype '{phrase}' (cosine {similarity:.2f})")
    return f"{', '.join(bits)} -> confidence {confidence:.2f}"


def _summary(
    key: str, confidence: float, matched: list[str], phrase: str, similarity: float
) -> str:
    name = settings.CATEGORY_BY_KEY[key]["name"]
    if matched:
        return (
            f"Classified as {name} ({confidence:.0%}). Keyword rule matched "
            f"'{matched[0]}' and the closest prototype '{phrase}' scored {similarity:.2f}."
        )
    return (
        f"Classified as {name} ({confidence:.0%}). Closest prototype '{phrase}' "
        f"scored {similarity:.2f} cosine similarity."
    )
