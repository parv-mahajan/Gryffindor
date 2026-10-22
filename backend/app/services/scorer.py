"""Explainable priority score (0-100).

score = 100 * sum(weight_i * factor_i)  + SLA escalation boost

Every factor is normalised to 0..1. The contribution of each factor (in
points) is returned so the UI can show "Safety +32, Wait +18".
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .. import settings
from .geo import haversine_m, zone_for_point


def _cue_score(text: str, cues: dict[str, float]) -> tuple[float, list[str]]:
    """Highest matching cue value plus the phrases that produced it."""
    hits = [(phrase, value) for phrase, value in cues.items() if phrase in text]
    if not hits:
        return 0.0, []
    best = max(value for _, value in hits)
    matched = sorted({phrase for phrase, value in hits if value >= best - 1e-9})
    return best, matched


def detect_impact(text: str, lat: float, lng: float) -> tuple[float, str]:
    """Community impact from the mentioned place, falling back to GPS zones."""
    lowered = text.lower()
    best_value = 0.0
    best_label = ""
    for label, value in settings.IMPACT_LOCATIONS.items():
        if label in lowered and value > best_value:
            best_value = value
            best_label = label
    if best_label:
        return best_value, f"location type '{best_label}' mentioned in the report"

    zone = zone_for_point(lat, lng)
    if zone:
        value = settings.IMPACT_LOCATIONS.get(zone["type"], settings.DEFAULT_IMPACT)
        return value, f"pin falls inside {zone['name']} ({zone['type']})"
    return settings.DEFAULT_IMPACT, "no high-impact location detected"


def safety_risk(text: str, category_key: str | None) -> tuple[float, list[str]]:
    base = 0.4
    if category_key and category_key in settings.CATEGORY_BY_KEY:
        base = settings.CATEGORY_BY_KEY[category_key]["safety"]
    cue_value, cue_hits = _cue_score(text, settings.SAFETY_CUES)
    if cue_value > base:
        return cue_value, cue_hits
    return base, cue_hits


def severity(text: str) -> tuple[float, list[str]]:
    value, hits = _cue_score(text, settings.SEVERITY_CUES)
    if value == 0.0:
        return 0.3, []
    return value, hits


def wait_time_factor(created_at: datetime, now: datetime | None = None) -> tuple[float, float]:
    """Log-scaled age in hours, capped at WAIT_TIME_CAP_HOURS."""
    now = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
    capped = min(hours, settings.WAIT_TIME_CAP_HOURS)
    factor = math.log1p(capped) / math.log1p(settings.WAIT_TIME_CAP_HOURS)
    return min(1.0, factor), hours


def related_reports_factor(count: int) -> float:
    return min(1.0, max(0, count) / settings.RELATED_REPORTS_CAP)


def score(
    *,
    description: str,
    category_key: str | None,
    lat: float,
    lng: float,
    created_at: datetime,
    related_reports: int = 0,
    resolved: bool = False,
    now: datetime | None = None,
) -> dict:
    """Compute the priority score and its full explanation."""
    now = now or datetime.now(timezone.utc)
    text = (description or "").lower()

    safety, safety_hits = safety_risk(text, category_key)
    sev, severity_hits = severity(text)
    impact, impact_reason = detect_impact(text, lat, lng)
    wait, age_hours = wait_time_factor(created_at, now)
    reports = related_reports_factor(related_reports)

    factors = {
        "safety_risk": round(safety, 4),
        "severity": round(sev, 4),
        "community_impact": round(impact, 4),
        "wait_time": round(wait, 4),
        "related_reports": round(reports, 4),
    }
    contributions = {
        name: round(100.0 * settings.PRIORITY_WEIGHTS[name] * value, 1)
        for name, value in factors.items()
    }

    base = sum(contributions.values())
    band = settings.band_for_score(base)

    sla_hours = settings.SLA_HOURS.get(band, 168)
    sla_due_at = created_at + timedelta(hours=sla_hours)
    breached = (not resolved) and now > sla_due_at
    boost = settings.SLA_BREACH_BOOST if breached else 0.0

    final = min(settings.MAX_PRIORITY_SCORE, base + boost)
    final_band = settings.band_for_score(final)

    explanation = {
        "factors": factors,
        "contributions": contributions,
        "labels": settings.PRIORITY_FACTOR_LABELS,
        "weights": settings.PRIORITY_WEIGHTS,
        "base_score": round(base, 1),
        "sla_boost": round(boost, 1),
        "sla_hours": sla_hours,
        "sla_due_at": sla_due_at.isoformat(),
        "sla_breached": breached,
        "age_hours": round(age_hours, 1),
        "evidence": {
            "safety_cues": safety_hits,
            "severity_cues": severity_hits,
            "impact_reason": impact_reason,
            "related_reports": related_reports,
        },
        "summary": _summary(contributions, boost),
    }

    return {
        "score": round(final, 1),
        "band": final_band,
        "factors": factors,
        "contributions": contributions,
        "sla_due_at": sla_due_at,
        "sla_breached": breached,
        "explanation": explanation,
    }


def _summary(contributions: dict[str, float], boost: float) -> str:
    parts = [
        f"{settings.PRIORITY_FACTOR_LABELS[name]} +{value:g}"
        for name, value in sorted(
            contributions.items(), key=lambda kv: kv[1], reverse=True
        )
    ]
    text = ", ".join(parts)
    if boost:
        text += f", SLA breach +{boost:g}"
    return text
