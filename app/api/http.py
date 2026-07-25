"""JSON response helpers for pyweber API routes."""

from __future__ import annotations

import json
import logging
from typing import Any

import pyweber as pw
from pyweber.models.response import Response
from pyweber.utils.types import ContentTypes

from app.schemas.errors import error_body

logger = logging.getLogger("ctd.api")


def api_route(app: pw.Pyweber, path: str, methods: list[str] | None = None, **kwargs):
    """Register JSON API route (content_type=json avoids pyweber HTML handoff)."""
    kwargs.setdefault("content_type", ContentTypes.json)
    return app.route(path, methods=methods or ["GET"], **kwargs)


def api_json(app: pw.Pyweber, data: Any, status: int = 200) -> Response:
    """Return JSON Response with current app cookies attached."""
    payload = data if isinstance(data, (dict, list)) else data
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")

    resp = Response(
        request=app.request,
        response_content=json.dumps(payload, default=str).encode("utf-8"),
        code=status,
        cookies=dict(app.cookies),
        response_type=ContentTypes.json,
        route=app.request.path if app.request else "/",
    )
    # Pyweber adds WWW-Authenticate: Basic on 401 → browser native login popup.
    # Our auth is cookie/JWT; strip it so the SPA login form is used instead.
    resp.headers.pop("WWW-Authenticate", None)
    if isinstance(getattr(resp, "http_status_code", None), str):
        resp.http_status_code = resp.http_status_code.split("\r\n", 1)[0]
    return resp


def api_error(
    app: pw.Pyweber,
    status: int,
    code: str,
    message: str,
    details: list[Any] | None = None,
) -> Response:
    path = app.request.path if app.request else "?"
    method = getattr(app.request, "method", "?") if app.request else "?"
    if status >= 500:
        logger.error("%s %s [%s] %s", method, path, code, message)
    else:
        logger.warning("%s %s [%s] %s", method, path, code, message)
    if details:
        logger.warning("details: %s", details)
    return api_json(app, error_body(code, message, details), status=status)
