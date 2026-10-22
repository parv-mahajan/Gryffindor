"""Password hashing and session tokens.

Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a per-user salt. A
login returns an opaque token that lives in the `auth_sessions` table, so a
session can be revoked by deleting the row.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import AuthSession, User

ITERATIONS = 120_000
ALGORITHM = "pbkdf2_sha256"
SESSION_HOURS = 12
TOKEN_BYTES = 24


def hash_password(password: str) -> str:
    """Return a self describing hash: algorithm$iterations$salt$digest."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Check a password against a stored hash."""
    if not stored:
        return False
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_session(db: Session, user: User) -> AuthSession:
    """Issue a token for a user."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    session = AuthSession(
        token=token,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def revoke_session(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token == token))
    db.commit()


def user_for_token(db: Session, token: str) -> User | None:
    """Resolve a token to its user, dropping the token when it has expired."""
    session = db.execute(
        select(AuthSession).where(AuthSession.token == token)
    ).scalar_one_or_none()
    if session is None:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        revoke_session(db, token)
        return None
    return session.user


def purge_expired(db: Session) -> int:
    result = db.execute(
        delete(AuthSession).where(AuthSession.expires_at < datetime.now(timezone.utc))
    )
    db.commit()
    return int(result.rowcount or 0)
