"""Synthetic seed data for CivicSense.

Creates ~150 complaints around one campus area with deliberate duplicate
groups, one obvious recurring hotspot, a realistic status/age mix and a
handful of vague low-confidence reports that need human review.

Usage:  python scripts/seed.py [--reset]
"""

from __future__ import annotations

import math
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geoalchemy2.shape import from_shape  # noqa: E402
from shapely.geometry import Point  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from app import config, settings  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.models import AuditLog, Complaint, ComplaintLink, Incident, User  # noqa: E402
from app.services import audit, classifier, embeddings, scorer  # noqa: E402
from app.services import duplicates as dupsvc  # noqa: E402
from app.services.geo import haversine_m  # noqa: E402

RNG = random.Random(20261022)
NOW = datetime.now(timezone.utc)

CAMPUS_LAT, CAMPUS_LNG = 19.0760, 72.8777

SPOTS = [
    ("main gate 2", 19.0763, 72.8834),
    ("central avenue junction", 19.0752, 72.8776),
    ("hospital road", 19.0790, 72.8798),
    ("hostel H3 block", 19.0702, 72.8742),
    ("hostel H5 block", 19.0812, 72.8726),
    ("school of engineering", 19.0748, 72.8790),
    ("lake view road", 19.0790, 72.8740),
    ("library crossing", 19.0770, 72.8790),
    ("canteen road", 19.0740, 72.8760),
    ("sports complex", 19.0830, 72.8790),
    ("main gate 1", 19.0730, 72.8720),
    ("PG hostel block", 19.0720, 72.8830),
    ("academic block", 19.0758, 72.8808),
    ("power house lane", 19.0778, 72.8748),
]

TEMPLATES: dict[str, list[str]] = {
    "pothole": [
        "Huge pothole on the main road near {loc}, bikes are skidding and two students fell yesterday",
        "There is a deep crater on the road near {loc}, vehicles hit it at speed",
        "Big pit in the road right next to {loc}, the road surface is completely broken",
        "Pothole right in the middle of the carriageway at {loc}, very dangerous for two wheelers",
        "Road has sunk and formed a large hole near {loc}, water collects inside it",
    ],
    "garbage": [
        "Garbage pile is overflowing near {loc}, the whole area is stinking",
        "Dustbins near {loc} are full and waste is dumped on the road",
        "Rotting garbage dumped near {loc}, flies and stray dogs everywhere",
        "Waste collection has not happened for a week at {loc}, bins are overflowing",
        "Illegal dumping of household waste near {loc}, very messy",
    ],
    "water_leak": [
        "Water pipe is leaking near {loc}, the whole road is flooded",
        "Burst pipe near {loc}, water is flowing on the road continuously",
        "Pipeline leaking for three days near {loc}, water is everywhere on the street",
        "Water supply pipe has burst at {loc}, the footpath is waterlogged",
        "Water is seeping from a broken main near {loc}, complete waterlogging",
    ],
    "streetlight": [
        "There is no light on the road near {loc} after 7 pm, it is completely dark",
        "Street light is not working near {loc}, the stretch is pitch dark at night",
        "Lamp post is dead near {loc}, no lights on this road since last week",
        "All the lights near {loc} are off, students walk in the dark",
        "Tubelight on the pole near {loc} keeps flickering and goes off",
    ],
    "drainage": [
        "Manhole is open without a cover near {loc}, very risky for pedestrians",
        "The drain is blocked near {loc} and sewage is overflowing",
        "Choked drain causing waterlogging at {loc} after every rain",
        "Open manhole with no barricade near {loc}, someone could fall in",
        "Drainage near {loc} is completely blocked, the road is flooded",
    ],
    "other": [
        "Broken bench and missing dustbin near {loc}, needs repair",
        "Faded zebra crossing markings near {loc}, not visible at night",
        "Loose handrail on the staircase near {loc}, needs fixing",
        "Broken tile floor near {loc}, someone slipped on it",
        "Damaged signboard near {loc}, half of it has fallen",
    ],
}

VAGUE = [
    "Problem near the gate, please check",
    "Not good condition here",
    "Something is wrong at this spot",
    "Urgent issue, see the photo",
    "Please look into this matter",
    "Same problem as before, still not fixed",
    "Bad condition of the road here",
    "Request immediate attention at this location",
]

STATUS_POOL = (
    ["resolved"] * 20
    + ["in_progress"] * 9
    + ["assigned"] * 8
    + ["triaged"] * 8
    + ["submitted"] * 7
)


def offset(lat: float, lng: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    dlat = dy_m / 111_320.0
    dlng = dx_m / (111_320.0 * math.cos(math.radians(lat)))
    return lat + dlat, lng + dlng


def age_days() -> float:
    """Old complaints are less common but not rare."""
    roll = RNG.random()
    if roll < 0.30:
        return RNG.uniform(0, 2)
    if roll < 0.60:
        return RNG.uniform(2, 7)
    if roll < 0.80:
        return RNG.uniform(7, 14)
    return RNG.uniform(14, 120)


def make_description(category: str, loc: str) -> str:
    return RNG.choice(TEMPLATES[category]).format(loc=loc)


def make_photo(name: str) -> str:
    """Write a small placeholder photo so the image pipeline has real inputs."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (320, 240), (110, 112, 116))
    draw = ImageDraw.Draw(img)
    draw.ellipse((90, 60, 230, 180), fill=(58, 58, 62))
    draw.text((10, 220), name, fill=(235, 235, 235))
    path = config.UPLOAD_DIR / name
    img.save(path)
    return name


def build_records(target: int = settings.SEED_COMPLAINTS) -> list[dict]:
    records: list[dict] = []

    def add(
        description: str,
        lat: float,
        lng: float,
        label: str | None,
        age: float,
        status: str | None = None,
        photo: bool = False,
        group: int | None = None,
        vague: bool = False,
    ) -> None:
        records.append(
            {
                "description": description,
                "lat": lat,
                "lng": lng,
                "label": label,
                "age_days": age,
                "status": status or RNG.choice(STATUS_POOL),
                "photo": photo,
                "group": group,
                "vague": vague,
            }
        )

    # 1. Deliberate duplicate groups: same issue, reworded, within ~25 m.
    duplicate_groups = [
        ("pothole", "main gate 2"),
        ("pothole", "central avenue junction"),
        ("garbage", "hostel H3 block"),
        ("garbage", "canteen road"),
        ("water_leak", "hospital road"),
        ("water_leak", "hostel H5 block"),
        ("streetlight", "library crossing"),
        ("streetlight", "lake view road"),
        ("drainage", "canteen road"),
        ("drainage", "main gate 1"),
        ("other", "library crossing"),
        ("pothole", "sports complex"),
        ("garbage", "PG hostel block"),
        ("streetlight", "academic block"),
    ]
    # The deliberate groups are the interesting part of the corpus, so their
    # number scales with the requested size instead of being truncated away.
    scale = max(0.25, target / float(settings.SEED_COMPLAINTS))
    group_count = max(4, int(len(duplicate_groups) * scale))
    for group_index, (category, loc_name) in enumerate(duplicate_groups[:group_count]):
        lat, lng = next((s[1], s[2]) for s in SPOTS if s[0] == loc_name)
        members = RNG.choice([2, 2, 3])
        base_description = RNG.choice(TEMPLATES[category]).format(loc=loc_name)
        for i in range(members):
            # reword slightly
            text = base_description
            if i == 1:
                text = base_description.replace("Huge", "Big").replace("huge", "big")
                text = text.replace("is not working", "has stopped working")
            elif i == 2:
                text = text.replace("there is", "there is a").replace("There is", "There is a")
            dlat, dlng = offset(lat, lng, RNG.uniform(-25, 25), RNG.uniform(-25, 25))
            add(
                text,
                dlat,
                dlng,
                category,
                RNG.uniform(0.5, 45),
                group=group_index,
            )

    # 2. Recurring hotspot: repeated potholes along central avenue over 5 months.
    for i in range(max(3, int(7 * scale))):
        lat, lng = offset(19.0752, 72.8752 + i * 0.00085, RNG.uniform(-12, 12), RNG.uniform(-18, 18))
        description = RNG.choice(
            [
                "Pothole on central avenue has appeared again near the {loc} stretch",
                "Road surface on central avenue near {loc} has broken into a pit",
                "Another deep pothole on central avenue close to {loc}",
                "Central avenue near {loc} has a large crater in the carriageway",
            ]
        ).format(loc="main gate 2")
        add(
            description,
            lat,
            lng,
            "pothole",
            RNG.uniform(8, 150),
        )

    # 3. Vague reports that must trigger "needs human review".
    for i, text in enumerate(VAGUE[: max(3, int(len(VAGUE) * scale))]):
        lat, lng = offset(CAMPUS_LAT, CAMPUS_LNG, RNG.uniform(-600, 600), RNG.uniform(-600, 600))
        add(
            text,
            lat,
            lng,
            "other",
            RNG.uniform(1, 90),
            photo=(i % 3 == 0),
            vague=True,
        )

    # 4. Ordinary reports to round the corpus out to 150.
    categories = list(TEMPLATES.keys())
    while len(records) < target:
        category = RNG.choice(categories)
        loc_name, lat, lng = RNG.choice(SPOTS)
        dlat, dlng = offset(lat, lng, RNG.uniform(-70, 70), RNG.uniform(-70, 70))
        add(
            make_description(category, loc_name),
            dlat,
            dlng,
            category,
            age_days(),
            photo=(RNG.random() < 0.06),
        )

    return records[:target]


def main() -> None:
    count = settings.SEED_COMPLAINTS
    if "--count" in sys.argv:
        count = int(sys.argv[sys.argv.index("--count") + 1])

    if "--reset" in sys.argv:
        print("Clearing complaints, incidents, links and audit log ...")
        with SessionLocal() as db:
            db.execute(delete(ComplaintLink))
            db.execute(delete(AuditLog))
            db.execute(delete(Complaint))
            db.execute(delete(Incident))
            db.commit()

    records = build_records(count)
    print(f"Generating {len(records)} complaints ...")

    descriptions = [r["description"] for r in records]
    print("Embedding descriptions (this loads the MiniLM model once) ...")
    vectors = embeddings.encode(descriptions)

    routing = {rule["category"]: rule for rule in settings.ROUTING_RULES}

    with SessionLocal() as db:
        admin = db.execute(select(User).where(User.username == "admin")).scalar_one()
        reporter = db.execute(select(User).where(User.username == "reporter")).scalar_one()

        group_state: dict[int, dict] = {}
        complaint_ids: dict[int, int] = {}

        for index, rec in enumerate(records):
            created_at = NOW - timedelta(days=rec["age_days"], hours=RNG.uniform(0, 23))
            status = rec["status"]
            resolved_at = None
            if status == "resolved":
                resolved_at = created_at + timedelta(days=RNG.uniform(0.5, 18))
                if resolved_at > NOW:
                    resolved_at = NOW - timedelta(hours=RNG.uniform(1, 48))

            label = rec["label"]
            classification = classifier.classify(rec["description"])
            category = classification["category"]
            department = routing[category]["department"] if category else None

            group = rec.get("group")
            related_reports = 0
            if group is not None:
                state = group_state.setdefault(group, {"members": []})
                related_reports = len(state["members"])

            priority = scorer.score(
                description=rec["description"],
                category_key=category,
                lat=rec["lat"],
                lng=rec["lng"],
                created_at=created_at,
                related_reports=related_reports,
                resolved=status == "resolved",
                now=NOW,
            )

            ticket_id = f"CS-S{index:04d}-{uuid.uuid4().hex[:4].upper()}"
            photos = []
            if rec["photo"]:
                photos.append(make_photo(f"seed_{index:04d}.png"))

            head = group_state.get(group, {}).get("head") if group is not None else None
            if head is None:
                incident = Incident(
                    ticket_id=f"INC-S{index:04d}-{uuid.uuid4().hex[:4].upper()}",
                    title=rec["description"][:120],
                    category_key=category,
                    location=from_shape(Point(rec["lng"], rec["lat"]), srid=4326),
                    status="resolved" if status == "resolved" else "open",
                    created_at=created_at,
                )
                db.add(incident)
                db.flush()
            else:
                incident = db.get(Incident, head["incident_id"])
                incident.merged_count = (incident.merged_count or 0) + 1

            complaint = Complaint(
                ticket_id=ticket_id,
                description=rec["description"],
                location=from_shape(Point(rec["lng"], rec["lat"]), srid=4326),
                lat=rec["lat"],
                lng=rec["lng"],
                status=status,
                incident_id=incident.id,
                category_key=category,
                category_confidence=classification["confidence"],
                category_explanation=classification["explanation"],
                category_alternatives=classification["alternatives"],
                needs_review=classification["needs_review"],
                image_scores=classification["image_scores"],
                model_version=classification["model_version"],
                priority_score=priority["score"],
                priority_band=priority["band"],
                priority_factors=priority["factors"],
                priority_contributions=priority["contributions"],
                department_key=department,
                sla_due_at=priority["sla_due_at"],
                reporter_name=RNG.choice(
                    ["Ananya S.", "Rohit M.", "Fatima K.", "Ishan P.", "Meera R.", None]
                ),
                reporter_contact=RNG.choice(
                    [None, None, "student@campus.edu", "resident@campus.edu"]
                ),
                reporter_user_id=reporter.id if RNG.random() < 0.5 else None,
                photos=photos,
                embedding=vectors[index].tolist(),
                created_at=created_at,
                updated_at=resolved_at or created_at,
                resolved_at=resolved_at,
            )
            db.add(complaint)
            db.flush()
            complaint_ids[index] = complaint.id

            if group is not None:
                state = group_state[group]
                if "head" not in state:
                    state["head"] = {
                        "complaint_id": complaint.id,
                        "incident_id": incident.id,
                        "lat": complaint.lat,
                        "lng": complaint.lng,
                    }
                else:
                    distance = round(
                        haversine_m(
                            complaint.lat,
                            complaint.lng,
                            state["head"]["lat"],
                            state["head"]["lng"],
                        ),
                        1,
                    )
                    db.add(
                        ComplaintLink(
                            complaint_id=complaint.id,
                            linked_complaint_id=state["head"]["complaint_id"],
                            relation="duplicate",
                            score=0.9,
                            text_similarity=0.9,
                            geo_proximity=0.8,
                            time_decay=0.8,
                            distance_m=distance,
                            status="accepted",
                            decided_at=NOW,
                            decided_by="seed",
                        )
                    )
                    audit.record(
                        db,
                        entity_type="complaint",
                        entity_id=complaint.id,
                        action="duplicates_detected",
                        actor="system",
                        new_value={
                            "related_reports": related_reports,
                            "candidates": [
                                {
                                    "ticket_id": db.get(
                                        Complaint, state["head"]["complaint_id"]
                                    ).ticket_id,
                                    "relation": "duplicate",
                                    "score": 0.9,
                                }
                            ],
                        },
                    )
                state["members"].append(index)

            audit.record(
                db,
                entity_type="complaint",
                entity_id=complaint.id,
                action="ai_classification",
                actor="system",
                old_value={"seed_label": label, "vague": rec.get("vague", False)},
                new_value={
                    "category": category,
                    "confidence": classification["confidence"],
                    "needs_review": classification["needs_review"],
                    "alternatives": classification["alternatives"],
                    "explanation": classification["explanation"],
                },
                reason="AI suggestion on intake",
                model_version=classification["model_version"],
                confidence=classification["confidence"],
            )
            audit.record(
                db,
                entity_type="complaint",
                entity_id=complaint.id,
                action="priority_scored",
                actor="system",
                new_value={
                    "score": priority["score"],
                    "band": priority["band"],
                    "contributions": priority["contributions"],
                },
                model_version=config.MODEL_VERSION,
            )
            if status != "submitted":
                audit.record(
                    db,
                    entity_type="complaint",
                    entity_id=complaint.id,
                    action="status_change",
                    actor=admin.username,
                    old_value="submitted",
                    new_value=status,
                )

        # Second pass: run the production duplicate detector over the whole
        # corpus in filing order. Group links already exist; this adds the
        # pending related/duplicate suggestions the dashboard can review.
        print("Running duplicate detection pass ...")
        linked_counts: dict[int, int] = {}
        for complaint in sorted(db.execute(select(Complaint)).scalars(), key=lambda c: c.created_at):
            candidates = dupsvc.find_candidates(
                db,
                description=complaint.description,
                category_key=complaint.category_key,
                lat=complaint.lat,
                lng=complaint.lng,
                created_at=complaint.created_at,
                exclude_ids={complaint.id},
            )
            fresh = 0
            for candidate in candidates:
                row = dupsvc.link(
                    db,
                    complaint=complaint,
                    candidate=candidate["complaint"],
                    relation=candidate["relation"],
                    score=candidate["score"],
                    text_similarity=candidate["text_similarity"],
                    geo_proximity=candidate["geo_proximity"],
                    time_decay=candidate["time_decay"],
                    distance_m=candidate["distance_m"],
                )
                is_new = row is not None and row.id is None
                # flush so the next direction check can see this row
                db.flush()
                if is_new:
                    fresh += 1
            if fresh:
                linked_counts[complaint.id] = linked_counts.get(complaint.id, 0) + fresh
                audit.record(
                    db,
                    entity_type="complaint",
                    entity_id=complaint.id,
                    action="duplicates_detected",
                    actor="system",
                    new_value={
                        "related_reports": linked_counts[complaint.id],
                        "candidates": [
                            {
                                "ticket_id": c["complaint"].ticket_id,
                                "relation": c["relation"],
                                "score": c["score"],
                                "distance_m": c["distance_m"],
                            }
                            for c in candidates[:5]
                        ],
                    },
                    model_version=config.MODEL_VERSION,
                    confidence=max(c["score"] for c in candidates),
                )

        # Complaints that gained links in the detection pass are re-scored,
        # because the number of related reports is a priority input.
        for complaint_id, count in linked_counts.items():
            complaint = db.get(Complaint, complaint_id)
            result = scorer.score(
                description=complaint.description,
                category_key=complaint.category_key,
                lat=complaint.lat,
                lng=complaint.lng,
                created_at=complaint.created_at,
                related_reports=count,
                resolved=complaint.status == "resolved",
                now=NOW,
            )
            complaint.priority_score = result["score"]
            complaint.priority_band = result["band"]
            complaint.priority_factors = result["factors"]
            complaint.priority_contributions = result["contributions"]
            audit.record(
                db,
                entity_type="complaint",
                entity_id=complaint.id,
                action="priority_scored",
                actor="system",
                new_value={
                    "score": result["score"],
                    "band": result["band"],
                    "contributions": result["contributions"],
                    "related_reports": count,
                },
                model_version=config.MODEL_VERSION,
            )

        db.commit()
        print("Seed committed.")

    with SessionLocal() as db:
        total = db.execute(select(Complaint)).scalars().all()
        print(f"complaints: {len(total)}")
        print(f"incidents: {db.execute(select(Incident)).scalars().unique().all().__len__()}")
        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        agree = 0
        labelled = 0
        for c in total:
            by_status[c.status] = by_status.get(c.status, 0) + 1
            by_category[c.category_key] = by_category.get(c.category_key, 0) + 1
            entry = db.execute(
                select(AuditLog).where(
                    AuditLog.entity_id == c.id, AuditLog.action == "ai_classification"
                )
            ).scalar_one_or_none()
            if entry and entry.old_value:
                labelled += 1
                if entry.old_value.get("seed_label") == c.category_key:
                    agree += 1
        print("by status:", by_status)
        print("by category:", by_category)
        print("needs review:", sum(1 for c in total if c.needs_review))
        print(
            f"classifier agreement with the seeded label: {agree}/{labelled} "
            f"({agree / labelled:.1%})" if labelled else "no labels"
        )


if __name__ == "__main__":
    main()
