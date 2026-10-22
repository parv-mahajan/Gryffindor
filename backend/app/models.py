"""SQLAlchemy models for the CivicSense schema."""

from __future__ import annotations

from datetime import datetime, timezone

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(16))  # admin | reporter
    display_name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(160), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    """Issued login token. Tokens expire and can be revoked by deleting the row."""

    __tablename__ = "auth_sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship("User", lazy="joined")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    capacity: Mapped[int] = mapped_column(Integer, default=20)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class RoutingRule(Base):
    __tablename__ = "routing_rules"
    __table_args__ = (UniqueConstraint("category_key", "priority_band", name="uq_rule_cat_band"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_key: Mapped[str] = mapped_column(String(32))
    priority_band: Mapped[str] = mapped_column(String(16), default="*")
    department_key: Mapped[str] = mapped_column(String(32))
    response_hours: Mapped[int] = mapped_column(Integer, default=72)
    priority: Mapped[int] = mapped_column(Integer, default=100)


class Incident(Base):
    """Parent group. Duplicates are attached to a parent, never deleted."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    category_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location: Mapped["Geography"] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), default="open")
    merged_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)

    location: Mapped["Geography"] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String(24), default="submitted", index=True)
    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # AI classification
    category_key: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    category_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    category_explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    category_alternatives: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    image_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Priority
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    priority_band: Mapped[str] = mapped_column(String(16), default="low", index=True)
    priority_factors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    priority_contributions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    priority_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_override_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Routing
    department_key: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reporter
    reporter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reporter_contact: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reporter_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    photos: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    embedding: Mapped[list | None] = mapped_column(ARRAY(Float), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped[Incident | None] = relationship("Incident", lazy="joined")


class ComplaintLink(Base):
    """Duplicate or related link between two complaints."""

    __tablename__ = "complaint_links"
    __table_args__ = (
        UniqueConstraint("complaint_id", "linked_complaint_id", name="uq_link_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True
    )
    linked_complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True
    )
    relation: Mapped[str] = mapped_column(String(16))  # duplicate | related
    score: Mapped[float] = mapped_column(Float, default=0.0)
    text_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    geo_proximity: Mapped[float] = mapped_column(Float, default=0.0)
    time_decay: Mapped[float] = mapped_column(Float, default=0.0)
    distance_m: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|accepted|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    """Append only audit trail."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(48), index=True)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
