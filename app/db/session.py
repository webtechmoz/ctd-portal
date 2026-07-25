"""Database session — re-exports bootstrap helpers."""

from app.db import bootstrap
from app.db.bootstrap import bootstrap_database, get_session, init_engine, run_migrations


def __getattr__(name: str):
    # Lazy attributes so callers always see post-bootstrap SessionLocal/engine
    if name == "SessionLocal":
        return bootstrap.SessionLocal
    if name == "engine":
        return bootstrap.engine
    raise AttributeError(name)


__all__ = [
    "SessionLocal",
    "bootstrap_database",
    "engine",
    "get_session",
    "init_engine",
    "run_migrations",
]
