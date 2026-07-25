"""CTD Portal — entry point (API-first pyweber).

Production (Railway):
  uvicorn main:app --host 0.0.0.0 --port $PORT

Local (pyweber server):
  python main.py
"""

from __future__ import annotations

import time

from config.settings import settings
from app.ssl_fix import apply_ssl_relax_if_configured
from app.pyweber_compat import apply_pyweber_compat
from app.logging_config import configure_logging, get_logger

apply_ssl_relax_if_configured()
apply_pyweber_compat()
configure_logging()

import pyweber as pw

from app.api.pages import html_page
from app.db.bootstrap import bootstrap_database

logger = get_logger("ctd")

# Pyweber instance (routes, static, cookies). Not the uvicorn target by itself —
# pyweber ASGI lifespan is a no-op, so we wrap it below.
pw_app = pw.Pyweber()
# Pyweber serves each dir as /{dirname}/... — keep asset URLs as /css /js /assets
pw_app.static("css", "js", "assets")


# --- Page routes (static HTML shells; logic lives in frontend/js) ---

@pw_app.route("/")
def home_page():
    return html_page("index.html")


@pw_app.route("/login")
def login_page():
    return html_page("login.html")


@pw_app.route("/avaliacao")
def avaliacao_page():
    return html_page("avaliacao.html")


@pw_app.route("/avaliacoes")
def avaliacoes_page():
    return html_page("avaliacoes.html")


@pw_app.route("/anexos")
def anexos_page():
    return html_page("anexos.html")


@pw_app.route("/projectos")
def projectos_page():
    return html_page("projectos.html")


@pw_app.route("/situacao")
def situacao_page():
    return html_page("situacao.html")


@pw_app.route("/dashboard")
def dashboard_page():
    return html_page("dashboard.html")


@pw_app.route("/admin")
def admin_page():
    return html_page("admin/index.html")


@pw_app.route("/admin/projectos/novo")
def admin_projecto_novo():
    return html_page("admin/projecto-form.html")


@pw_app.route("/admin/projectos/{projecto_id}")
def admin_projecto_editar(projecto_id):
    return html_page("admin/projecto-form.html")


# --- API registration ---
from app.api import register_api_routes

register_api_routes(pw_app)


@pw_app.route("/api/v1/health", methods=["GET"])
def health():
    """Health check for Railway / load balancers."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
    }


def _should_access_log(path: str) -> bool:
    if not path:
        return True
    # Reduz ruido de estaticos no terminal
    for prefix in ("/css/", "/js/", "/assets/", "/_pyweber/"):
        if path.startswith(prefix):
            return False
    return True


async def app(scope, receive, send):
    """ASGI entry for uvicorn: lifespan bootstrap + delegate to pyweber.

    Use: uvicorn main:app --host 0.0.0.0 --port $PORT
    """
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    bootstrap_database()
                    configure_logging(force=True)
                    logger.info(
                        "ASGI startup ok — %s (%s)",
                        settings.APP_NAME,
                        settings.APP_ENV,
                    )
                    await send({"type": "lifespan.startup.complete"})
                except Exception as exc:
                    logger.exception("Database bootstrap failed on startup")
                    await send(
                        {
                            "type": "lifespan.startup.failed",
                            "message": str(exc),
                        }
                    )
            elif message["type"] == "lifespan.shutdown":
                logger.info("ASGI shutdown")
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    if scope["type"] != "http":
        await pw_app(scope, receive, send)
        return

    method = scope.get("method", "?")
    path = scope.get("path", "?")
    status_code = 500
    started = time.perf_counter()

    async def send_wrapper(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = int(message.get("status") or 500)
        await send(message)

    try:
        await pw_app(scope, receive, send_wrapper)
    except Exception:
        ms = (time.perf_counter() - started) * 1000
        logger.exception("%s %s → EXC (%.0fms)", method, path, ms)
        raise
    else:
        if _should_access_log(path):
            ms = (time.perf_counter() - started) * 1000
            level = logging_level_for_status(status_code)
            logger.log(level, "%s %s → %s (%.0fms)", method, path, status_code, ms)


def logging_level_for_status(status: int) -> int:
    import logging as _logging

    if status >= 500:
        return _logging.ERROR
    if status >= 400:
        return _logging.WARNING
    return _logging.INFO


# Backwards-compatible alias used by some auth helpers that import `app`
# from main — prefer pw_app inside this module; API modules receive pw_app
# via register(app=...).
# Keep `app` as the ASGI callable for uvicorn.


if __name__ == "__main__":
    # Local pyweber server (does not use the ASGI lifespan wrapper)
    bootstrap_database()
    configure_logging(force=True)
    logger.info(
        "Starting %s (%s) on %s:%s",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.APP_HOST,
        settings.bind_port,
    )
    pw_app.run()
