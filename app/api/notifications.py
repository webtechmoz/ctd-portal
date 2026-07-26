"""Notifications API."""

from app.api.http import api_error, api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.services import auth_service
from app.services import notification_service as notif_svc

API_PREFIX = "/api/v1"


def register(app):
    @api_route(app, f"{API_PREFIX}/notifications", methods=["GET"])
    def list_notifications():
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                notif_svc.sync_due_avaliacoes(session, ctx.user)
                notif_svc.sync_pending_validations(session, ctx.user)
                rows = notif_svc.list_for_user(session, ctx.user.id)
                unread = notif_svc.count_unread(session, ctx.user.id)
                return api_json(
                    app,
                    {
                        "unread": unread,
                        "notifications": [
                            {
                                "id": n.id,
                                "tipo": n.tipo,
                                "titulo": n.titulo,
                                "corpo": n.corpo,
                                "link": n.link,
                                "lida": n.lida,
                                "created_at": n.created_at.isoformat() if n.created_at else None,
                            }
                            for n in rows
                        ],
                    },
                )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/notifications/{{notif_id}}/read", methods=["POST"])
    def read_one(notif_id):
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                ok = notif_svc.mark_read(session, ctx.user.id, int(notif_id))
                if not ok:
                    return api_error(app, 404, "NOT_FOUND", "Notificacao nao encontrada.")
                return api_json(app, {"ok": True})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/notifications/read-all", methods=["POST"])
    def read_all():
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                n = notif_svc.mark_all_read(session, ctx.user.id)
                return api_json(app, {"ok": True, "count": n})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
