"""Dashboard API — Fase 2."""

from app.api.http import api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.services import auth_service
from app.services.dashboard_service import build_dashboard

API_PREFIX = "/api/v1"


def register(app):
    @api_route(app, f"{API_PREFIX}/pilares/{{pilar_id}}/dashboard", methods=["GET"])
    def pilar_dashboard(pilar_id):
        try:
            with session_scope() as session:
                require_auth(app, session)
                data = build_dashboard(session, int(pilar_id))
                return api_json(app, data.model_dump(mode="json"))
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
