"""Workflow operations: triage, assignment, review decisions and link merges.

Every state change goes through here so the audit trail stays complete and the
priority score is recomputed whenever the inputs change.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import settings
from ..models import Complaint, ComplaintLink
from . import audit, scorer


class WorkflowError(Exception):
    """Raised when a transition is not allowed."""


def route_for(category_key: str | None) -> tuple[str | None, int]:
    """Department and response window for a category."""
    for rule in settings.ROUTING_RULES:
        if rule["category"] == category_key:
            return rule["department"], rule["response_hours"]
    return None, settings.SLA_HOURS.get("low", 168)


def apply_routing(
    db: Session,
    complaint: Complaint,
    *,
    department_key: str | None = None,
    actor: str = "system",
) -> None:
    """Set the department and SLA deadline from the routing rules."""
    if department_key is None:
        department_key, response_hours = route_for(complaint.category_key)
    else:
        _, response_hours = route_for(complaint.category_key)
    old_department = complaint.department_key
    complaint.department_key = department_key
    if complaint.created_at:
        complaint.sla_due_at = complaint.created_at + timedelta(hours=response_hours)
    if old_department != department_key:
        audit.record(
            db,
            entity_type="complaint",
            entity_id=complaint.id,
            action="routed",
            actor=actor,
            old_value={"department_key": old_department},
            new_value={"department_key": department_key, "response_hours": response_hours},
        )


def rescore(
    db: Session,
    complaint: Complaint,
    *,
    related_reports: int = 0,
    actor: str = "system",
) -> dict:
    """Recompute the priority score and store the explanation."""
    previous = complaint.priority_score
    result = scorer.score(
        description=complaint.description,
        category_key=complaint.category_key,
        lat=complaint.lat,
        lng=complaint.lng,
        created_at=complaint.created_at,
        related_reports=related_reports,
        resolved=complaint.status == "resolved",
    )
    complaint.priority_score = result["score"]
    complaint.priority_band = result["band"]
    complaint.priority_factors = result["factors"]
    complaint.priority_contributions = result["contributions"]
    complaint.sla_due_at = result["sla_due_at"]
    audit.record(
        db,
        entity_type="complaint",
        entity_id=complaint.id,
        action="priority_scored",
        actor=actor,
        old_value={"score": previous},
        new_value={
            "score": result["score"],
            "band": result["band"],
            "contributions": result["contributions"],
            "explanation": result["explanation"],
        },
        model_version=complaint.model_version,
    )
    return result


def transition(
    db: Session,
    complaint: Complaint,
    new_status: str,
    *,
    actor: str = "system",
    reason: str | None = None,
    department_key: str | None = None,
) -> Complaint:
    """Move a complaint through the lifecycle."""
    if new_status not in settings.STATUSES:
        raise WorkflowError(f"Unknown status '{new_status}'")
    if new_status == complaint.status:
        raise WorkflowError(f"Complaint is already '{new_status}'")
    allowed = settings.STATUS_TRANSITIONS.get(complaint.status, [])
    if new_status not in allowed:
        raise WorkflowError(
            f"Cannot move from '{complaint.status}' to '{new_status}' "
            f"(allowed: {', '.join(allowed)})"
        )

    old_status = complaint.status
    now = datetime.now(timezone.utc)
    complaint.status = new_status
    complaint.updated_at = now

    if new_status == "resolved":
        complaint.resolved_at = now
    elif old_status == "resolved":
        complaint.resolved_at = None

    if new_status == "assigned":
        complaint.assigned_at = now
        if department_key:
            apply_routing(db, complaint, department_key=department_key, actor=actor)
    elif new_status in {"triaged", "in_progress"}:
        apply_routing(db, complaint, department_key=department_key, actor=actor)

    if complaint.incident is not None:
        incident = complaint.incident
        incident.status = "resolved" if new_status == "resolved" else "open"
        incident.updated_at = now
        incident.category_key = complaint.category_key or incident.category_key

    audit.record(
        db,
        entity_type="complaint",
        entity_id=complaint.id,
        action="status_change",
        actor=actor,
        old_value={"status": old_status},
        new_value={"status": new_status, "department_key": complaint.department_key},
        reason=reason,
    )
    rescore(db, complaint, related_reports=accepted_link_count(db, complaint.id), actor=actor)
    return complaint


def apply_review(
    db: Session,
    complaint: Complaint,
    *,
    category_key: str,
    actor: str,
    reason: str | None = None,
    confirm: bool = True,
) -> dict:
    """Accept or override the AI category and clear the review flag."""
    if category_key not in settings.CATEGORY_BY_KEY:
        raise WorkflowError(f"Unknown category '{category_key}'")

    old_category = complaint.category_key
    old_confidence = complaint.category_confidence
    old_review = complaint.needs_review

    complaint.category_key = category_key
    complaint.needs_review = False
    if not confirm:
        # A human override - the model was wrong, so the stored confidence is
        # no longer meaningful.
        complaint.category_confidence = 1.0
        explanation = dict(complaint.category_explanation or {})
        explanation["review"] = {
            "decided_by": actor,
            "decision": "category_overridden",
            "model_category": old_category,
            "model_confidence": old_confidence,
            "reason": reason,
        }
        complaint.category_explanation = explanation

    apply_routing(db, complaint, actor=actor)
    audit.record(
        db,
        entity_type="complaint",
        entity_id=complaint.id,
        action="review_decision",
        actor=actor,
        old_value={
            "category_key": old_category,
            "needs_review": old_review,
            "confidence": old_confidence,
        },
        new_value={
            "category_key": category_key,
            "needs_review": False,
            "decision": "confirmed" if confirm else "overridden",
        },
        reason=reason,
        confidence=complaint.category_confidence,
    )
    rescore(db, complaint, related_reports=accepted_link_count(db, complaint.id), actor=actor)
    return {
        "ticket_id": complaint.ticket_id,
        "category_key": complaint.category_key,
        "needs_review": complaint.needs_review,
        "decision": "confirmed" if confirm else "overridden",
    }


def accepted_link_count(db: Session, complaint_id: int) -> int:
    """How many links of this complaint are already accepted."""
    from sqlalchemy import func, or_

    return int(
        db.execute(
            select(func.count())
            .select_from(ComplaintLink)
            .where(
                or_(
                    ComplaintLink.complaint_id == complaint_id,
                    ComplaintLink.linked_complaint_id == complaint_id,
                ),
                ComplaintLink.status == "accepted",
            )
        ).scalar_one()
    )


def decide_link(
    db: Session,
    link: ComplaintLink,
    *,
    decision: str,
    actor: str,
    reason: str | None = None,
) -> dict:
    """Accept or reject a suggested duplicate link.

    Accepting merges the newer complaint into the older incident and refreshes
    the priority score of both, because the number of related reports is a
    scoring input.
    """
    if decision not in {"accepted", "rejected"}:
        raise WorkflowError(f"Unknown decision '{decision}'")

    link.status = decision
    link.decided_at = datetime.now(timezone.utc)
    link.decided_by = actor
    link.decision_reason = reason

    complaints = {
        row.id: row
        for row in db.execute(
            select(Complaint).where(
                Complaint.id.in_([link.complaint_id, link.linked_complaint_id])
            )
        ).scalars()
    }
    older = complaints.get(link.complaint_id)
    newer = complaints.get(link.linked_complaint_id)
    if older is None or newer is None:
        raise WorkflowError("Linked complaint is missing")

    if older.created_at <= newer.created_at:
        primary, secondary = older, newer
    else:
        primary, secondary = newer, older

    merged = False
    if decision == "accepted":
        if primary.incident is not None:
            secondary.incident_id = primary.incident_id
            primary.incident.merged_count = (primary.incident.merged_count or 0) + 1
            primary.incident.updated_at = datetime.now(timezone.utc)
        merged = True
    # The session runs with autoflush disabled, so the new link status and the
    # incident merge must be flushed before the re-score reads them back.
    db.flush()

    audit.record(
        db,
        entity_type="complaint_link",
        entity_id=link.id,
        action="link_decision",
        actor=actor,
        old_value={"status": "pending"},
        new_value={
            "status": decision,
            "relation": link.relation,
            "score": link.score,
            "primary_ticket": primary.ticket_id,
            "secondary_ticket": secondary.ticket_id,
            "merged": merged,
        },
        reason=reason,
        confidence=link.score,
    )
    for complaint in (primary, secondary):
        rescore(
            db,
            complaint,
            related_reports=accepted_link_count(db, complaint.id),
            actor=actor,
        )
    return {
        "link_id": link.id,
        "status": decision,
        "merged": merged,
        "primary_ticket": primary.ticket_id,
        "secondary_ticket": secondary.ticket_id,
    }
