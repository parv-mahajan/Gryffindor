"""Pydantic schemas for the public API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CategoryScore(BaseModel):
    key: str
    name: str
    confidence: float
    explanation: str


class ComplaintCreate(BaseModel):
    description: str = Field(min_length=5, max_length=4000)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    reporter_name: str | None = Field(default=None, max_length=120)
    reporter_contact: str | None = Field(default=None, max_length=160)


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    description: str
    status: str
    lat: float
    lng: float
    incident_id: int | None
    category_key: str | None
    category_confidence: float | None
    category_explanation: dict[str, Any] | None
    category_alternatives: list[dict[str, Any]] | None
    needs_review: bool
    image_scores: dict[str, Any] | None
    model_version: str | None
    priority_score: float
    priority_band: str
    priority_factors: dict[str, Any] | None
    priority_contributions: dict[str, Any] | None
    priority_overridden: bool
    department_key: str | None
    sla_due_at: datetime | None
    reporter_name: str | None
    reporter_contact: str | None
    photos: list[str] | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class ComplaintCreateResponse(BaseModel):
    ticket_id: str
    complaint: ComplaintOut
    classification: dict[str, Any] | None = None
    priority: dict[str, Any] | None = None
    duplicates: list[dict[str, Any]] = Field(default_factory=list)


class TicketStatusOut(BaseModel):
    ticket_id: str
    status: str
    category: str | None
    category_confidence: float | None
    priority_band: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    last_update: str | None
    department: str | None = None
    incident_ticket_id: str | None = None
    grouped_reports: int = 0


class StatusChangeRequest(BaseModel):
    status: str
    reason: str | None = None
    department_key: str | None = None


class ReviewRequest(BaseModel):
    category_key: str
    confirm: bool = True
    reason: str | None = None


class LinkDecisionRequest(BaseModel):
    decision: str
    reason: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class SessionOut(BaseModel):
    token: str
    username: str
    role: str
    display_name: str
    expires_at: datetime
