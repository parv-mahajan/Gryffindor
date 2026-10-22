"""Authentication helpers.

The caller is identified by the session token handed out by `POST /auth/login`,
sent as `Authorization: Bearer <token>`. Only admins may drive the workflow.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .services import auth


def get_actor(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the acting user from the bearer token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue",
        )

    token = authorization.split()[-1] if " " in authorization else authorization.strip()
    user = auth.user_for_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired, sign in again",
        )
    return user


def require_admin(actor: User = Depends(get_actor)) -> User:
    if actor.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return actor


def optional_actor(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve the caller when a session is present, without demanding one.

    Public endpoints (reporting an issue, tracking a ticket) work signed out;
    when a session is sent the complaint is tied to that account.
    """
    if not authorization:
        return None
    token = authorization.split()[-1] if " " in authorization else authorization.strip()
    return auth.user_for_token(db, token)


def actor_label(actor: User | None) -> str:
    return actor.username if actor else "system"
