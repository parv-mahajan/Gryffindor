"""Small geographic helpers shared by the scorer, deduper and clusterer."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6371008.8


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def zone_for_point(lat: float, lng: float) -> dict | None:
    """Return the campus zone containing the point, if any."""
    from ..settings import CAMPUS_ZONES

    best = None
    for zone in CAMPUS_ZONES:
        d = haversine_m(lat, lng, zone["lat"], zone["lng"])
        if d <= zone["radius"] and (best is None or d < best[0]):
            best = (d, zone)
    return best[1] if best else None
