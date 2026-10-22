"""Single source of truth for categories, rules, weights and thresholds.

Every tunable number the platform uses lives in this file. Nothing else in the
code base is allowed to hard-code a weight, a threshold or a category list.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------
# keywords  -> rule layer, wins when it fires (obvious cases)
# prototypes-> embedded once at startup, used for cosine similarity
# safety    -> base safety risk for the category (0..1)
# department-> routing default
CATEGORIES: list[dict] = [
    {
        "key": "pothole",
        "name": "Pothole",
        "description": "Broken road surface: pits, holes, cracks, damaged surface.",
        "department": "roads",
        "safety": 0.85,
        "keywords": [
            "pothole", "potholes", "pot hole", "pit", "pits", "hole in road",
            "road is broken", "broken road", "crater",
            "uneven road", "bumpy road", "road surface",
            "road has sunk", "road collapse",
        ],
        "prototypes": [
            "There is a large pothole on the road and vehicles are skidding.",
            "Deep pit in the middle of the carriageway near the junction.",
            "The road surface is broken and full of craters.",
            "Big hole on the road shoulder after the monsoon.",
            "Road has collapsed and formed a dangerous pit.",
        ],
    },
    {
        "key": "garbage",
        "name": "Garbage / Sanitation",
        "description": "Waste accumulation, overflowing bins, illegal dumping.",
        "department": "sanitation",
        "safety": 0.55,
        "keywords": [
            "garbage", "rubbish", "waste", "trash", "litter", "dumped waste",
            "dumping", "overflowing bin", "overflowing garbage", "sewage waste",
            "stinking garbage", "rotting waste", "garbage pile", "waste pile",
            "garbage bin", "dustbin is", "dustbins are", "dustbin is full",
            "bins are", "bin is full", "waste is dumped", "garbage is piled",
            "waste collection", "garbage collection", "illegal dumping",
        ],
        "prototypes": [
            "Garbage is piled up on the road and is not being collected.",
            "The dustbin near the hostel is overflowing with rubbish.",
            "People are dumping waste in an open area.",
            "There is rotting garbage and a bad smell near the canteen.",
            "Household waste is dumped on the street corner.",
        ],
    },
    {
        "key": "water_leak",
        "name": "Water Leak / Supply",
        "description": "Leaking or burst pipes, waterlogging, low water supply.",
        "department": "water",
        "safety": 0.75,
        "keywords": [
            "water leak", "leaking water", "leaking pipe", "pipe is leaking",
            "burst pipe", "pipe burst", "water is leaking", "waterlogging",
            "water logged", "flooding", "flooded", "water stagnation",
            "no water supply", "water supply", "sewage overflow",
            "water seeping", "water on the road", "tank empty", "water tanker",
            "leaking", "pipeline leaking", "water is everywhere", "water everywhere",
        ],
        "prototypes": [
            "A water pipe is leaking on the main road and water is everywhere.",
            "The pipeline has burst and the whole street is flooded.",
            "There is waterlogging near the gate because of a broken pipe.",
            "Water supply has been completely stopped in the hostel block.",
            "Sewage water is overflowing onto the footpath.",
        ],
    },
    {
        "key": "streetlight",
        "name": "Streetlight",
        "description": "Non-working or missing street lights.",
        "department": "electrical",
        "safety": 0.65,
        "keywords": [
            "street light", "streetlight", "street lights", "no light",
            "light is not working", "light not working", "lamp is off",
            "lamp post", "lamppost", "light pole", "lights are off",
            "dark stretch", "no streetlight", "light is dead", "broken light",
            "tubelight", "light is flickering", "flickering light", "lights",
            "lamp is", "lamps are", "not lit", "unlit",
        ],
        "prototypes": [
            "There is no light on this stretch of road at night.",
            "The street light is not working and the area is completely dark.",
            "Street lights near the gate have been off for a week.",
            "The lamp post is broken and the whole road is dark.",
            "Lights are flickering and going off intermittently.",
        ],
    },
    {
        "key": "drainage",
        "name": "Drainage / Manhole",
        "description": "Blocked drains, open or missing manholes, sewage.",
        "department": "drainage",
        "safety": 0.80,
        "keywords": [
            "drain", "drains", "drainage", "manhole", "man hole", "manhole cover",
            "open manhole", "manhole is open", "sewer", "sewage", "gutter",
            "blocked drain", "drain is blocked", "water drain", "choked drain",
            "drainage blocked", "storm drain",
        ],
        "prototypes": [
            "The manhole cover is missing and the hole is open on the road.",
            "The drain is blocked and the whole area is waterlogged.",
            "Sewage is overflowing from the choked drain near the hostel.",
            "An open manhole without a cover is a hazard for pedestrians.",
            "The drainage system is completely blocked after the rain.",
        ],
    },
    {
        "key": "other",
        "name": "Other",
        "description": "Anything that does not match a specific category.",
        "department": "general",
        "safety": 0.45,
        "keywords": [
            "broken bench", "bench is broken", "handrail", "staircase",
            "stair rail", "signboard", "zebra crossing", "crossing marking",
            "tile floor", "broken tile", "fence is broken", "flood gate",
            "playground equipment", "drinking water point", "notice board",
            "paver block", "compound wall", "dustbin is missing",
            "missing dustbin", "broken swing", "swings", "water cooler",
        ],
        "prototypes": [
            "A broken bench and a missing dustbin need repair.",
            "The zebra crossing markings have faded and are not visible at night.",
            "The handrail on the staircase is loose and needs fixing.",
            "The notice signboard has fallen down and needs to be put back.",
            "The floor tiles near the gate are broken and someone slipped on them.",
        ],
    },
]

CATEGORY_KEYS = [c["key"] for c in CATEGORIES]
CATEGORY_BY_KEY = {c["key"]: c for c in CATEGORIES}
# --------------------------------------------------------------------------
# Departments and routing rules
# --------------------------------------------------------------------------
DEPARTMENTS: list[dict] = [
    {"key": "roads", "name": "Roads & Paving", "capacity": 40},
    {"key": "sanitation", "name": "Sanitation", "capacity": 35},
    {"key": "water", "name": "Water Supply", "capacity": 25},
    {"key": "electrical", "name": "Electrical", "capacity": 20},
    {"key": "drainage", "name": "Drainage", "capacity": 22},
    {"key": "general", "name": "General Maintenance", "capacity": 30},
]

DEPARTMENTS_BY_KEY = {d["key"]: d for d in DEPARTMENTS}

# category -> department, and urgency band -> target response time (hours)
ROUTING_RULES: list[dict] = [
    {"category": "pothole", "department": "roads", "response_hours": 72},
    {"category": "garbage", "department": "sanitation", "response_hours": 24},
    {"category": "water_leak", "department": "water", "response_hours": 12},
    {"category": "streetlight", "department": "electrical", "response_hours": 48},
    {"category": "drainage", "department": "drainage", "response_hours": 24},
    {"category": "other", "department": "general", "response_hours": 120},
]

# --------------------------------------------------------------------------
# Priority model
# --------------------------------------------------------------------------
# Weights must sum to 1.0 (validated at import time).
PRIORITY_WEIGHTS: dict[str, float] = {
    "safety_risk": 0.30,
    "severity": 0.25,
    "community_impact": 0.20,
    "wait_time": 0.15,
    "related_reports": 0.10,
}

PRIORITY_FACTOR_LABELS: dict[str, str] = {
    "safety_risk": "Safety",
    "severity": "Severity",
    "community_impact": "Impact",
    "wait_time": "Wait",
    "related_reports": "Reports",
}

# SLA hours per priority band (target response time).
SLA_HOURS: dict[str, int] = {
    "critical": 24,
    "high": 72,
    "medium": 168,
    "low": 336,
}

# Points added when a complaint outlives the SLA of its band.
SLA_BREACH_BOOST = 8.0
MAX_PRIORITY_SCORE = 100.0

# Band boundaries, highest first.
PRIORITY_BANDS: list[tuple[str, float]] = [
    ("critical", 75.0),
    ("high", 50.0),
    ("medium", 25.0),
    ("low", 0.0),
]

# wait_time is log scaled and capped at this many hours.
WAIT_TIME_CAP_HOURS = 240.0
# related_reports saturates at this many linked reports.
RELATED_REPORTS_CAP = 5.0

# Keyword cues that raise or lower severity / safety regardless of category.
SEVERITY_CUES: dict[str, float] = {
    "deep": 0.8, "huge": 0.85, "giant": 0.9, "massive": 0.85, "large": 0.6,
    "severe": 0.9, "dangerous": 0.9, "danger": 0.85, "worst": 0.8,
    "very bad": 0.8, "completely": 0.6, "burst": 0.9, "flood": 0.9,
    "flooding": 0.9, "collapsed": 0.9, "sparking": 0.95, "fire": 0.95,
    "burning": 0.9, "smoke": 0.85, "snake": 0.9, "accident": 0.9,
    "injured": 0.9, "child": 0.6, "children": 0.6, "school kids": 0.7,
    "electric": 0.85, "live wire": 0.95, "exposed wire": 0.95,
    "stagnant": 0.7, "rotting": 0.65, "smell": 0.5, "for weeks": 0.7,
    "for months": 0.75, "every day": 0.6, "blocked completely": 0.75,
}
SAFETY_CUES: dict[str, float] = {
    "live wire": 0.95, "exposed wire": 0.95, "sparking": 0.95, "fire": 0.95,
    "snake": 0.9, "collapsed": 0.9, "open manhole": 0.85, "without cover": 0.85,
    "manhole is open": 0.85, "flood": 0.8, "flooding": 0.8, "accident": 0.85,
    "dangerous": 0.8, "broken glass": 0.6, "electric": 0.8, "gas": 0.85,
    "uncovered": 0.75, "sharp": 0.6, "sinkhole": 0.9,
}

# Location type -> community impact factor (0..1). Applied when the report
# text mentions the place, or when the pin falls inside a campus zone.
IMPACT_LOCATIONS: dict[str, float] = {
    "hospital": 1.0, "clinic": 0.9, "ambulance": 0.95, "medical centre": 0.95,
    "school": 0.85, "college": 0.8, "university": 0.8, "playground": 0.65,
    "hostel": 0.75, "mess": 0.65, "canteen": 0.6, "market": 0.65,
    "bus stop": 0.6, "main road": 0.7, "main gate": 0.65, "gate": 0.6,
    "junction": 0.6, "crossroad": 0.6, "bridge": 0.65, "railway": 0.6,
    "residential": 0.45, "laboratory": 0.7, "library": 0.7, "temple": 0.6,
}
DEFAULT_IMPACT = 0.35

# Named zones on the seeded campus: (name, type, lat, lng, radius_m)
CAMPUS_ZONES: list[dict] = [
    {"name": "Institute Hospital", "type": "hospital", "lat": 19.0790, "lng": 72.8798, "radius": 90},
    {"name": "School of Engineering", "type": "school", "lat": 19.0748, "lng": 72.8790, "radius": 110},
    {"name": "Hostel H3 Block", "type": "hostel", "lat": 19.0702, "lng": 72.8742, "radius": 120},
    {"name": "Hostel H5 Block", "type": "hostel", "lat": 19.0812, "lng": 72.8726, "radius": 120},
    {"name": "Main Gate 2", "type": "main gate", "lat": 19.0763, "lng": 72.8834, "radius": 80},
    {"name": "Central Avenue", "type": "main road", "lat": 19.0752, "lng": 72.8776, "radius": 150},
    {"name": "Lake View Road", "type": "main road", "lat": 19.0790, "lng": 72.8740, "radius": 140},
]

# --------------------------------------------------------------------------
# Classification thresholds
# --------------------------------------------------------------------------
# Below this top-1 confidence the complaint is flagged for human review.
REVIEW_MIN_CONFIDENCE = 0.50
# If top1 - top2 is smaller than this the decision is ambiguous.
REVIEW_MIN_TOP_GAP = 0.08
# A keyword hit is trusted outright when it is this specific.
KEYWORD_CONFIDENCE = 0.95
# Weight of the keyword rule layer vs the embedding similarity.
KEYWORD_BLEND = 0.62

# The embedding score is gated by how strongly the text matches the closest
# prototype at all (absolute gate) and by how much information the report
# actually carries (specificity). Both stop vague one-liners from looking
# confident.
ABSOLUTE_GATE_LOW = 0.42
ABSOLUTE_GATE_SPAN = 0.25
SPECIFICITY_CONTENT_WORDS = 6.0

# --------------------------------------------------------------------------
# Duplicate / related detection
# --------------------------------------------------------------------------
DUPLICATE = {
    "candidate_radius_m": 100.0,
    "candidate_days": 14,
    "weights": {"text": 0.5, "geo": 0.3, "time": 0.2},
    "likely_duplicate_score": 0.78,
    "likely_duplicate_max_distance_m": 30.0,
    "related_min_score": 0.45,
    "text_min_similarity": 0.35,
}

# --------------------------------------------------------------------------
# Clustering / hotspots
# --------------------------------------------------------------------------
CLUSTERING = {
    "eps_m": 60.0,
    "min_samples": 3,
    "hotspot_min_incidents": 3,
    "hotspot_min_months": 2,
    "hotspot_radius_m": 120.0,
}

# --------------------------------------------------------------------------
# Lifecycle
# --------------------------------------------------------------------------
STATUSES: list[str] = ["submitted", "triaged", "assigned", "in_progress", "resolved"]
STATUS_TRANSITIONS: dict[str, list[str]] = {
    "submitted": ["triaged", "assigned", "in_progress", "resolved"],
    "triaged": ["assigned", "in_progress", "resolved", "submitted"],
    "assigned": ["in_progress", "resolved", "triaged"],
    "in_progress": ["resolved", "assigned"],
    "resolved": ["in_progress"],
}
OPEN_STATUSES = ["submitted", "triaged", "assigned", "in_progress"]


# --------------------------------------------------------------------------
# Seed data
# --------------------------------------------------------------------------
# How many complaints the seed script generates. The corpus is deliberately
# small enough to stay readable in the dashboard while still covering every
# category, lifecycle status, duplicate group and hotspot.
SEED_COMPLAINTS = 60


def band_for_score(score: float) -> str:
    """Map a 0-100 priority score onto its band."""
    for name, threshold in PRIORITY_BANDS:
        if score >= threshold:
            return name
    return "low"


def validate_settings() -> None:
    total = sum(PRIORITY_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"PRIORITY_WEIGHTS must sum to 1.0, got {total}"
    assert set(PRIORITY_WEIGHTS) == set(PRIORITY_FACTOR_LABELS)
    for category in CATEGORIES:
        assert category["department"] in {d["key"] for d in DEPARTMENTS}


validate_settings()
