"""Login and session endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuthSession, User
from ..schemas import LoginRequest, SessionOut
from ..services import audit, auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SessionOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> SessionOut:
    """Exchange a username and password for a session token."""
    user = db.execute(
        select(User).where(User.username == payload.username.strip())
    ).scalar_one_or_none()

    # The same message for an unknown user and a wrong password, so the
    # endpoint does not tell an attacker which usernames exist.
    if user is None or not auth.verify_password(payload.password, user.password_hash):
        audit.record(
            db,
            entity_type="user",
            entity_id=user.id if user else 0,
            action="login_failed",
            actor=payload.username[:64],
            reason="invalid credentials",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong username or password",
        )

    session = auth.create_session(db, user)
    audit.record(
        db,
        entity_type="user",
        entity_id=user.id,
        action="login",
        actor=user.username,
        new_value={"role": user.role},
    )
    db.commit()
    return SessionOut(
        token=session.token,
        username=user.username,
        role=user.role,
        display_name=user.display_name,
        expires_at=session.expires_at,
    )


@router.get("/me", response_model=SessionOut)
def whoami(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> SessionOut:
    """Return the session behind the bearer token."""
    token = _bearer(authorization)
    user = auth.user_for_token(db, token) if token else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    session = db.execute(
        select(AuthSession).where(AuthSession.token == token)
    ).scalar_one()
    return SessionOut(
        token=token,
        username=user.username,
        role=user.role,
        display_name=user.display_name,
        expires_at=session.expires_at,
    )


@router.post("/logout")
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """Revoke the token that was used for this request."""
    token = _bearer(authorization)
    if token:
        auth.revoke_session(db, token)
    return {"status": "signed out"}


def _bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return authorization.strip()
