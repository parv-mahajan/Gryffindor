"""Complaint submission, listing and detail."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config, settings
from ..db import get_db
from ..deps import optional_actor, require_admin
from ..models import Complaint, ComplaintLink, Incident, User
from ..schemas import (
    ComplaintCreateResponse,
    ComplaintOut,
    LinkDecisionRequest,
    ReviewRequest,
    StatusChangeRequest,
)
from ..services import audit, classifier, duplicates, scorer, workflow

router = APIRouter(prefix="/complaints", tags=["complaints"])


def serialize(complaint: Complaint) -> ComplaintOut:
    return ComplaintOut.model_validate(complaint)


def _new_ticket_id() -> str:
    return f"CS-{uuid.uuid4().hex[:8].upper()}"


def _store_photos(files: list[UploadFile]) -> list[str]:
    saved: list[str] = []
    for upload in files or []:
        if not upload.filename:
            continue
        suffix = ""
        if "." in upload.filename:
            suffix = "." + upload.filename.rsplit(".", 1)[-1][:8]
        name = f"{uuid.uuid4().hex}{suffix}"
        path = config.UPLOAD_DIR / name
        path.write_bytes(upload.file.read())
        saved.append(name)
    return saved


@router.post("", response_model=ComplaintCreateResponse, status_code=201)
async def create_complaint(
    description: str = Form(..., min_length=5, max_length=4000),
    lat: float = Form(...),
    lng: float = Form(...),
    reporter_name: str | None = Form(default=None),
    reporter_contact: str | None = Form(default=None),
    photos: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
    actor: User | None = Depends(optional_actor),
) -> ComplaintCreateResponse:
    """Submit a new complaint. Classification and scoring are attached in Phase 2."""
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise HTTPException(status_code=422, detail="Invalid coordinates")

    now = datetime.now(timezone.utc)
    ticket_id = _new_ticket_id()

    stored_photos = _store_photos(photos or [])
    photo_paths = [str(config.UPLOAD_DIR / name) for name in stored_photos]

    classification = classifier.classify(description.strip(), photo_paths)
    category_key = classification["category"]

    # Duplicate / related detection runs before the score so the number of
    # related reports can feed the priority model.
    candidates = duplicates.find_candidates(
        db,
        description=description.strip(),
        category_key=category_key,
        lat=lat,
        lng=lng,
        created_at=now,
    )
    related_reports = len(candidates)

    priority = scorer.score(
        description=description,
        category_key=category_key,
        lat=lat,
        lng=lng,
        created_at=now,
        related_reports=related_reports,
    )

    complaint = Complaint(
        ticket_id=ticket_id,
        description=description.strip(),
        location=from_shape(Point(lng, lat), srid=4326),
        lat=lat,
        lng=lng,
        status="submitted",
        reporter_name=reporter_name,
        reporter_contact=reporter_contact,
        reporter_user_id=actor.id if actor else None,
        photos=stored_photos,
        category_key=category_key,
        category_confidence=classification["confidence"],
        category_explanation=classification["explanation"],
        category_alternatives=classification["alternatives"],
        needs_review=classification["needs_review"],
        image_scores=classification["image_scores"],
        model_version=classification["model_version"],
        embedding=classification["embedding"],
        priority_score=priority["score"],
        priority_band=priority["band"],
        priority_factors=priority["factors"],
        priority_contributions=priority["contributions"],
        sla_due_at=priority["sla_due_at"],
        created_at=now,
        updated_at=now,
    )
    db.add(complaint)
    db.flush()

    # Route it straight away so the department workload is complete from the
    # moment the report arrives.
    workflow.apply_routing(db, complaint, actor=actor.username if actor else "system")

    # A likely duplicate joins the incident of the report it repeats, so the
    # whole cluster is worked as one job instead of three.
    primary = next((c for c in candidates if c["relation"] == "duplicate"), None)
    incident = None
    if primary is not None and primary["complaint"].incident_id:
        incident = db.get(Incident, primary["complaint"].incident_id)
    if incident is None:
        incident = Incident(
            ticket_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            title=description.strip()[:120],
            category_key=category_key,
            location=from_shape(Point(lng, lat), srid=4326),
            status="open",
            created_at=now,
        )
        db.add(incident)
        db.flush()
    complaint.incident_id = incident.id
    if primary is not None:
        incident.merged_count = (incident.merged_count or 0) + 1

    for candidate in candidates:
        duplicates.link(
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
    if candidates:
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
                        "ticket_id": c["complaint"].ticket_id,
                        "relation": c["relation"],
                        "score": c["score"],
                        "text_similarity": c["text_similarity"],
                        "distance_m": c["distance_m"],
                    }
                    for c in candidates[:5]
                ],
            },
        model_version=classification["model_version"],
        confidence=max(c["score"] for c in candidates),
        )

    audit.record(
        db,
        entity_type="complaint",
        entity_id=complaint.id,
        action="complaint_submitted",
        actor=actor.username if actor else "anonymous",
        new_value={
            "ticket_id": ticket_id,
            "status": "submitted",
            "photos": len(stored_photos),
        },
    )
    audit.record(
        db,
        entity_type="complaint",
        entity_id=complaint.id,
        action="ai_classification",
        actor="system",
        new_value={
            "category": category_key,
            "confidence": classification["confidence"],
            "needs_review": classification["needs_review"],
            "alternatives": classification["alternatives"],
            "explanation": classification["explanation"],
        },
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
            "explanation": priority["explanation"],
        },
        model_version=classification["model_version"],
    )
    db.commit()
    db.refresh(complaint)

    return ComplaintCreateResponse(
        ticket_id=ticket_id,
        complaint=serialize(complaint),
        classification={
            "category": classification["category"],
            "category_name": classification["category_name"],
            "confidence": classification["confidence"],
            "explanation": classification["explanation"],
            "alternatives": classification["alternatives"],
            "needs_review": classification["needs_review"],
        },
        priority=priority["explanation"],
        duplicates=[
            {
                "ticket_id": c["complaint"].ticket_id,
                "relation": c["relation"],
                "score": c["score"],
                "text_similarity": c["text_similarity"],
                "geo_proximity": c["geo_proximity"],
                "time_decay": c["time_decay"],
                "distance_m": c["distance_m"],
            }
            for c in candidates
        ],
    )


@router.get("", response_model=list[ComplaintOut])
def list_complaints(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    department: str | None = Query(default=None),
    q: str | None = Query(default=None, description="free text search"),
    needs_review: bool | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> list[ComplaintOut]:
    stmt = select(Complaint)
    if status_filter:
        stmt = stmt.where(Complaint.status == status_filter)
    if category:
        stmt = stmt.where(Complaint.category_key == category)
    if department:
        stmt = stmt.where(Complaint.department_key == department)
    if needs_review is not None:
        stmt = stmt.where(Complaint.needs_review == needs_review)
    if q:
        stmt = stmt.where(Complaint.description.ilike(f"%{q}%"))

    stmt = stmt.order_by(
        Complaint.priority_score.desc(), Complaint.created_at.desc()
    ).limit(limit).offset(offset)
    return [serialize(c) for c in db.execute(stmt).scalars().all()]


@router.get("/stats/overview")
def overview(
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> dict:
    total = db.execute(select(func.count()).select_from(Complaint)).scalar_one()
    open_count = db.execute(
        select(func.count()).select_from(Complaint).where(
            Complaint.status != "resolved"
        )
    ).scalar_one()
    review = db.execute(
        select(func.count()).select_from(Complaint).where(Complaint.needs_review.is_(True))
    ).scalar_one()
    pending_links = db.execute(
        select(func.count()).select_from(ComplaintLink).where(ComplaintLink.status == "pending")
    ).scalar_one()
    return {
        "total": total,
        "open": open_count,
        "needs_review": review,
        "pending_links": pending_links,
    }


@router.get("/stats/workload")
def workload(
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> list[dict]:
    """Open load per department against the configured capacity."""
    rows = db.execute(
        select(
            Complaint.department_key,
            Complaint.status,
            func.count(),
            func.avg(Complaint.priority_score),
        )
        .where(Complaint.status != "resolved")
        .group_by(Complaint.department_key, Complaint.status)
    ).all()

    buckets: dict[str, dict] = {}
    for department_key, status, count, avg_score in rows:
        key = department_key or "unassigned"
        bucket = buckets.setdefault(
            key,
            {
                "department_key": key,
                "name": settings.DEPARTMENTS_BY_KEY.get(key, {}).get("name", "Unassigned"),
                "capacity": settings.DEPARTMENTS_BY_KEY.get(key, {}).get("capacity", 0),
                "open": 0,
                "by_status": {},
                "avg_priority": 0.0,
                "overdue": 0,
            },
        )
        bucket["open"] += count
        bucket["by_status"][status] = count
        bucket["avg_priority"] = max(bucket["avg_priority"], float(avg_score or 0))

    now = datetime.now(timezone.utc)
    overdue_rows = db.execute(
        select(Complaint.department_key, func.count())
        .where(
            Complaint.status != "resolved",
            Complaint.sla_due_at.isnot(None),
            Complaint.sla_due_at < now,
        )
        .group_by(Complaint.department_key)
    ).all()
    overdue_map = {key: count for key, count in overdue_rows}

    for key, bucket in buckets.items():
        bucket["overdue"] = overdue_map.get(key, 0)
        bucket["utilisation"] = (
            round(bucket["open"] / bucket["capacity"], 3) if bucket["capacity"] else None
        )
        bucket["avg_priority"] = round(bucket["avg_priority"], 1)

    return sorted(buckets.values(), key=lambda b: b["open"], reverse=True)


@router.get("/stats/hotspots")
def hotspots(
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> list[dict]:
    """Recurring clusters: the same category reported in one place again and again."""
    rows = db.execute(select(Complaint)).scalars().all()
    return duplicates.cluster_hotspots(rows)


@router.get("/links")
def list_links(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> list[dict]:
    """Duplicate suggestions waiting for a human decision."""
    stmt = select(ComplaintLink)
    if status_filter:
        stmt = stmt.where(ComplaintLink.status == status_filter)
    stmt = stmt.order_by(ComplaintLink.score.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()

    ids = {row.complaint_id for row in rows} | {row.linked_complaint_id for row in rows}
    complaints = {
        c.id: c
        for c in db.execute(select(Complaint).where(Complaint.id.in_(ids))).scalars()
    } if ids else {}

    out: list[dict] = []
    for row in rows:
        first = complaints.get(row.complaint_id)
        second = complaints.get(row.linked_complaint_id)
        out.append(
            {
                "id": row.id,
                "complaint_id": row.complaint_id,
                "linked_complaint_id": row.linked_complaint_id,
                "relation": row.relation,
                "score": row.score,
                "text_similarity": row.text_similarity,
                "geo_proximity": row.geo_proximity,
                "time_decay": row.time_decay,
                "distance_m": row.distance_m,
                "status": row.status,
                "first": {
                    "ticket_id": first.ticket_id if first else None,
                    "description": first.description if first else None,
                    "category_key": first.category_key if first else None,
                    "status": first.status if first else None,
                    "created_at": first.created_at.isoformat() if first else None,
                },
                "second": {
                    "ticket_id": second.ticket_id if second else None,
                    "description": second.description if second else None,
                    "category_key": second.category_key if second else None,
                    "status": second.status if second else None,
                    "created_at": second.created_at.isoformat() if second else None,
                },
            }
        )
    return out


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> ComplaintOut:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return serialize(complaint)


@router.get("/{complaint_id}/links")
def get_complaint_links(
    complaint_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> list[dict]:
    from ..models import ComplaintLink

    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    rows = db.execute(
        select(ComplaintLink).where(
            (ComplaintLink.complaint_id == complaint_id)
            | (ComplaintLink.linked_complaint_id == complaint_id)
        )
    ).scalars().all()
    return [
        {
            "id": link.id,
            "complaint_id": link.complaint_id,
            "linked_complaint_id": link.linked_complaint_id,
            "relation": link.relation,
            "score": link.score,
            "text_similarity": link.text_similarity,
            "geo_proximity": link.geo_proximity,
            "time_decay": link.time_decay,
            "distance_m": link.distance_m,
            "status": link.status,
        }
        for link in rows
    ]


@router.patch("/{complaint_id}/status")
def change_status(
    complaint_id: int,
    payload: StatusChangeRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> ComplaintOut:
    """Move a complaint through the lifecycle."""
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    try:
        workflow.transition(
            db,
            complaint,
            payload.status,
            actor=actor.username,
            reason=payload.reason,
            department_key=payload.department_key,
        )
    except workflow.WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(complaint)
    return serialize(complaint)


@router.post("/{complaint_id}/review")
def review_complaint(
    complaint_id: int,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> dict:
    """Confirm or override the category of a complaint that needs review."""
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    try:
        result = workflow.apply_review(
            db,
            complaint,
            category_key=payload.category_key,
            actor=actor.username,
            reason=payload.reason,
            confirm=payload.confirm,
        )
    except workflow.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(complaint)
    result["complaint"] = serialize(complaint).model_dump(mode="json")
    return result


@router.post("/links/{link_id}/decision")
def decide_link(
    link_id: int,
    payload: LinkDecisionRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> dict:
    """Accept or reject a suggested duplicate link."""
    link = db.get(ComplaintLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    try:
        result = workflow.decide_link(
            db,
            link,
            decision=payload.decision,
            actor=actor.username,
            reason=payload.reason,
        )
    except workflow.WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return result
