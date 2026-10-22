"""Public ticket lookup - no auth required, minimal data exposed."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Complaint, ComplaintLink, Incident
from ..schemas import TicketStatusOut

router = APIRouter(prefix="/tickets", tags=["public"])


@router.get("/{ticket_id}", response_model=TicketStatusOut)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> TicketStatusOut:
    complaint = db.execute(
        select(Complaint).where(Complaint.ticket_id == ticket_id.upper())
    ).scalar_one_or_none()
    if complaint is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    last_update = db.execute(
        select(ComplaintLink)
        .where(
            (ComplaintLink.complaint_id == complaint.id)
            | (ComplaintLink.linked_complaint_id == complaint.id)
        )
        .limit(1)
    ).scalar_one_or_none()

    grouped = 0
    incident_ticket_id = None
    if complaint.incident_id:
        incident = db.get(Incident, complaint.incident_id)
        if incident is not None:
            incident_ticket_id = incident.ticket_id
            grouped = db.execute(
                select(func.count())
                .select_from(Complaint)
                .where(Complaint.incident_id == incident.id)
            ).scalar_one()

    return TicketStatusOut(
        ticket_id=complaint.ticket_id,
        status=complaint.status,
        category=complaint.category_key,
        category_confidence=complaint.category_confidence,
        priority_band=complaint.priority_band,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
        resolved_at=complaint.resolved_at,
        last_update=(
            "Linked to another report" if last_update else None
        ),
        department=complaint.department_key,
        incident_ticket_id=incident_ticket_id,
        grouped_reports=grouped,
    )
