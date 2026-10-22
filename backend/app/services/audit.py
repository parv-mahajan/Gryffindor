"""Append-only audit trail helper."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditLog


def record(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    actor: str = "system",
    old_value: Any = None,
    new_value: Any = None,
    reason: str | None = None,
    model_version: str | None = None,
    confidence: float | None = None,
) -> AuditLog:
    """Write one audit row. The table is never updated or deleted."""
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        model_version=model_version,
        confidence=confidence,
    )
    db.add(entry)
    return entry
