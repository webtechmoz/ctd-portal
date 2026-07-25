"""Database bootstrap: ensure DB exists, engine, auto-migrations."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BOOTSTRAP_LOCK = threading.Lock()
_BOOTSTRAPPED = False

engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def ensure_mysql_database() -> None:
    """Create MySQL database if it does not exist (local only)."""
    if not settings.uses_mysql:
        return

    import pymysql

    connection = pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        charset=settings.MYSQL_CHARSET,
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.MYSQL_DATABASE}` "
                f"CHARACTER SET {settings.MYSQL_CHARSET} "
                f"COLLATE {settings.MYSQL_CHARSET}_unicode_ci"
            )
        logger.info("MySQL database ensured: %s", settings.MYSQL_DATABASE)
    finally:
        connection.close()


def run_migrations() -> None:
    """Apply Alembic migrations to head. Required on every boot."""
    versions_dir = _PROJECT_ROOT / "alembic" / "versions"
    has_revisions = any(
        p.suffix == ".py" and p.name != "__init__.py"
        for p in versions_dir.glob("*.py")
    )
    if not has_revisions:
        logger.warning(
            "Nenhuma migration em alembic/versions — skip"
        )
        return

    from alembic import command
    from alembic.config import Config

    alembic_ini = _PROJECT_ROOT / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))
    # ConfigParser treats % as interpolation — URL-encoded passwords use %XX
    url = settings.sqlalchemy_database_url.replace("%", "%%")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    logger.info("Alembic migrations applied (head)")


def init_engine() -> Engine:
    global engine, SessionLocal

    if settings.uses_mysql:
        ensure_mysql_database()

    engine = create_engine(
        settings.sqlalchemy_database_url,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine


def bootstrap_database(*, force: bool = False) -> Engine:
    """Full startup sequence: ensure DB → engine → migrations.

    Idempotent — safe under uvicorn workers / repeated lifespan + __main__.
    """
    global _BOOTSTRAPPED

    with _BOOTSTRAP_LOCK:
        if _BOOTSTRAPPED and not force and SessionLocal is not None and engine is not None:
            return engine

        eng = init_engine()
        if settings.AUTO_MIGRATE:
            run_migrations()
        settings.validate_for_boot()
        try:
            from app.services.seed_service import run_seed

            run_seed()
        except Exception:
            logger.exception("Seed automatico falhou")
            raise
        _BOOTSTRAPPED = True
        logger.info("Database bootstrap complete")
        return eng


def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call bootstrap_database() first.")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
