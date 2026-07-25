"""Token blacklist repository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import TokenBlacklist


def is_blacklisted(session: Session, jti: str) -> bool:
    row = session.scalar(select(TokenBlacklist).where(TokenBlacklist.jti == jti))
    return row is not None


def add(session: Session, jti: str, expires_at: datetime) -> None:
    if is_blacklisted(session, jti):
        return
    session.add(
        TokenBlacklist(
            jti=jti,
            expires_at=expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
    )
