"""Logging setup — stdout/stderr visible in terminal and Railway logs."""

from __future__ import annotations

import logging
import sys


_CONFIGURED = False


def configure_logging(*, force: bool = False) -> None:
    """Ensure app + uvicorn logs reach the terminal after Alembic fileConfig."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    root = logging.getLogger()
    # Alembic fileConfig often sets root to WARN and disables other loggers.
    root.setLevel(logging.INFO)
    root.disabled = False

    formatter = logging.Formatter(
        fmt="%(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Prefer a single stderr StreamHandler we control
    has_stream = False
    for h in list(root.handlers):
        if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) in (
            sys.stderr,
            sys.stdout,
        ):
            h.setLevel(logging.INFO)
            h.setFormatter(formatter)
            has_stream = True
        # Keep other handlers but lift level
        elif isinstance(h, logging.Handler):
            h.setLevel(logging.INFO)

    if not has_stream:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        root.addHandler(handler)

    for name, level in (
        ("ctd", logging.INFO),
        ("app", logging.INFO),
        ("uvicorn", logging.INFO),
        ("uvicorn.error", logging.INFO),
        ("uvicorn.access", logging.INFO),
        ("sqlalchemy.engine", logging.WARNING),
        ("alembic", logging.INFO),
    ):
        lg = logging.getLogger(name)
        lg.disabled = False
        lg.setLevel(level)
        # Avoid double-printing if a child had propagate=False after fileConfig
        lg.propagate = True

    _CONFIGURED = True


def get_logger(name: str = "ctd") -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
