"""Shared error schema helpers."""

from __future__ import annotations

from typing import Any


def error_body(code: str, message: str, details: list[Any] | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }
