"""Database session context helper."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session

from app.db import bootstrap as db


def ensure_db() -> None:
    """Lazy bootstrap — survives pyweber hot-reload (resets module globals)."""
    if db.SessionLocal is None:
        db.bootstrap_database()


@contextmanager
def session_scope() -> Iterator[Session]:
    ensure_db()
    session = db.SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
