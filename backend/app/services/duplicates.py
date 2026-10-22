"""Duplicate and related-report detection.

A candidate is a complaint of the same category that was filed close enough in
space and time. The final score blends three signals:

* text similarity - cosine between the sentence embeddings;
* geo proximity  - 1 at the same spot, decaying to 0 at the candidate radius;
* time decay     - 1 for a fresh report, decaying over the candidate window.

A candidate that clears the duplicate thresholds becomes a `duplicate` link and
is folded into the existing incident; anything weaker but still relevant stays
a `related` link.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import settings
from ..models import Complaint, ComplaintLink
from . import embeddings
from .geo import haversine_m

CONFIG = settings.DUPLICATE


def _geo_score(distance_m: float) -> float:
    radius = CONFIG["candidate_radius_m"]
    if radius <= 0:
        return 0.0
    return max(0.0, 1.0 - distance_m / radius)


def _time_score(age_hours: float) -> float:
    window_hours = CONFIG["candidate_days"] * 24.0
    if window_hours <= 0:
        return 0.0
    return max(0.0, 1.0 - age_hours / window_hours)


def _combine(text: float, geo: float, time: float) -> float:
    weights = CONFIG["weights"]
    return (
        weights["text"] * text
        + weights["geo"] * geo
        + weights["time"] * time
    )


def _relation(score: float, distance_m: float, text_similarity: float) -> str | None:
    """Return "duplicate" / "related" when the candidate is worth linking."""
    if text_similarity < CONFIG["text_min_similarity"]:
        return None
    if (
        score >= CONFIG["likely_duplicate_score"]
        and distance_m <= CONFIG["likely_duplicate_max_distance_m"]
    ):
        return "duplicate"
    if score >= CONFIG["related_min_score"]:
        return "related"
    return None


def find_candidates(
    db: Session,
    *,
    description: str,
    category_key: str | None,
    lat: float,
    lng: float,
    created_at: datetime | None = None,
    exclude_ids: set[int] | None = None,
) -> list[dict]:
    """Score every plausible candidate for a new complaint.

    Returns a list of dicts sorted by descending score with the relation type,
    the component scores and the matched candidate.
    """
    created_at = created_at or datetime.now(timezone.utc)
    window_start = created_at - timedelta(days=CONFIG["candidate_days"])

    stmt = (
        select(Complaint)
        .where(
            Complaint.created_at >= window_start,
            Complaint.created_at <= created_at,
            Complaint.embedding.isnot(None),
        )
        .order_by(Complaint.created_at.desc())
        .limit(2000)
    )
    if category_key:
        stmt = stmt.where(Complaint.category_key == category_key)
    if exclude_ids:
        stmt = stmt.where(Complaint.id.notin_(exclude_ids))

    candidates = db.execute(stmt).scalars().all()
    if not candidates:
        return []

    vector = np.asarray(embeddings.encode([description])[0], dtype=np.float32)
    now = datetime.now(timezone.utc)
    results: list[dict] = []

    for candidate in candidates:
        distance = haversine_m(lat, lng, candidate.lat, candidate.lng)
        if distance > CONFIG["candidate_radius_m"]:
            continue
        similarity = embeddings.cosine(vector, candidate.embedding or [])
        if similarity < CONFIG["text_min_similarity"]:
            continue
        age_hours = max(0.0, (now - candidate.created_at).total_seconds() / 3600.0)
        geo = _geo_score(distance)
        time = _time_score(age_hours)
        score = _combine(similarity, geo, time)
        relation = _relation(score, distance, similarity)
        if relation is None:
            continue
        results.append(
            {
                "complaint": candidate,
                "relation": relation,
                "score": round(score, 4),
                "text_similarity": round(similarity, 4),
                "geo_proximity": round(geo, 4),
                "time_decay": round(time, 4),
                "distance_m": round(distance, 1),
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results


def link(
    db: Session,
    *,
    complaint: Complaint,
    candidate: Complaint,
    relation: str,
    score: float,
    text_similarity: float,
    geo_proximity: float,
    time_decay: float,
    distance_m: float,
) -> ComplaintLink | None:
    """Create a link row between two complaints (idempotent, either direction)."""
    from sqlalchemy import and_, or_

    existing = db.execute(
        select(ComplaintLink).where(
            or_(
                and_(
                    ComplaintLink.complaint_id == complaint.id,
                    ComplaintLink.linked_complaint_id == candidate.id,
                ),
                and_(
                    ComplaintLink.complaint_id == candidate.id,
                    ComplaintLink.linked_complaint_id == complaint.id,
                ),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    row = ComplaintLink(
        complaint_id=complaint.id,
        linked_complaint_id=candidate.id,
        relation=relation,
        score=score,
        text_similarity=text_similarity,
        geo_proximity=geo_proximity,
        time_decay=time_decay,
        distance_m=distance_m,
        status="pending",
    )
    db.add(row)
    return row


def cluster_hotspots(
    complaints: list[Complaint],
    *,
    eps_m: float | None = None,
    min_samples: int | None = None,
) -> list[dict]:
    """Greedy single-link clustering on the incident locations.

    Reports of the same category that keep coming back in one place are the
    hotspot signal: a cluster that keeps re-filling over several months is a
    maintenance problem, not a one-off complaint.
    """
    eps = eps_m if eps_m is not None else settings.CLUSTERING["eps_m"]
    min_pts = min_samples if min_samples is not None else settings.CLUSTERING["min_samples"]

    groups: list[list[Complaint]] = []
    for complaint in complaints:
        placed = False
        for group in groups:
            head = group[0]
            if (
                head.category_key == complaint.category_key
                and haversine_m(head.lat, head.lng, complaint.lat, complaint.lng) <= eps
            ):
                group.append(complaint)
                placed = True
                break
        if not placed:
            groups.append([complaint])

    hotspots: list[dict] = []
    for group in groups:
        if len(group) < min_pts:
            continue
        lat = sum(c.lat for c in group) / len(group)
        lng = sum(c.lng for c in group) / len(group)
        days = {(c.created_at.date() - datetime(2000, 1, 1, tzinfo=timezone.utc).date()).days
                 for c in group}
        months = len({(d // 30) for d in days})
        age_days = [
            (datetime.now(timezone.utc) - c.created_at).days for c in group
        ]
        hotspots.append(
            {
                "category_key": group[0].category_key,
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "count": len(group),
                "months_active": months,
                "oldest_days": max(age_days) if age_days else 0,
                "ticket_ids": [c.ticket_id for c in group[:6]],
            }
        )
    hotspots.sort(key=lambda h: h["count"], reverse=True)
    return hotspots
