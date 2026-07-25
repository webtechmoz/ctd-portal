"""Pilares API — list / detail / create / update."""

from pydantic import ValidationError

from app.api.http import api_error, api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.models.enums import UserRole
from app.repositories import pilares as pilar_repo
from app.schemas.pilar import PilarListItem, PilarUpdate, PilarWrite
from app.schemas.pilar_master import PilarMasterOut
from app.services import auth_service
from app.services import pilar_service
from app.services.rbac_service import user_has_permission

API_PREFIX = "/api/v1"


def _body(request):
    body = getattr(request, "body", None) or {}
    if not isinstance(body, dict):
        return {}
    nested = body.get("body")
    if isinstance(nested, dict):
        return nested
    return body


def _require_manage(session, user) -> None:
    if user_has_permission(session, user, "projectos.manage"):
        return
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role == UserRole.admin.value:
        return
    raise auth_service.AuthError("FORBIDDEN", "Sem permissao para gerir projectos.", 403)


def _require_perm(session, user, code: str, message: str) -> None:
    if user_has_permission(session, user, code) or user_has_permission(
        session, user, "projectos.manage"
    ):
        return
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role == UserRole.admin.value:
        return
    raise auth_service.AuthError("FORBIDDEN", message, 403)


def register(app):
    @api_route(app, f"{API_PREFIX}/pilares", methods=["GET", "POST"])
    def pilares(request):
        method = (app.request.method if app.request else "GET").upper()
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                if method == "GET":
                    # Admin UI uses /pilares/admin-list for inactive+active
                    rows = pilar_repo.list_activos(session)
                    items = [
                        PilarListItem.model_validate(p).model_dump(mode="json") for p in rows
                    ]
                    return api_json(app, {"pilares": items})

                _require_manage(session, ctx.user)
                try:
                    data = PilarWrite.model_validate(_body(request))
                except ValidationError as exc:
                    return api_error(
                        app,
                        422,
                        "VALIDATION_ERROR",
                        "Dados do projecto invalidos.",
                        details=exc.errors(include_url=False, include_context=False),
                    )
                result = pilar_service.create_pilar(session, data)
                return api_json(app, {"pilar": result.model_dump(mode="json")}, status=201)
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/admin/pilares", methods=["GET"])
    def pilares_admin_list():
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                _require_manage(session, ctx.user)
                items = [
                    PilarListItem.model_validate(p).model_dump(mode="json")
                    for p in pilar_repo.list_all(session)
                ]
                return api_json(app, {"pilares": items})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/pilares/{{pilar_id}}", methods=["GET", "PATCH", "DELETE"])
    def pilar_one(pilar_id):
        method = (app.request.method if app.request else "GET").upper()
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                if method == "GET":
                    pilar = pilar_repo.get_with_master(session, int(pilar_id))
                    if not pilar:
                        return api_error(app, 404, "NOT_FOUND", "Pilar nao encontrado.")
                    return api_json(
                        app,
                        {"pilar": PilarMasterOut.model_validate(pilar).model_dump(mode="json")},
                    )

                if method == "DELETE":
                    _require_perm(
                        session,
                        ctx.user,
                        "projectos.delete",
                        "Sem permissao para apagar projectos.",
                    )
                    pilar_service.delete_pilar(session, int(pilar_id))
                    return api_json(app, {"ok": True})

                try:
                    data = PilarUpdate.model_validate(_body(app.request))
                except ValidationError as exc:
                    return api_error(
                        app,
                        422,
                        "VALIDATION_ERROR",
                        "Dados do projecto invalidos.",
                        details=exc.errors(include_url=False, include_context=False),
                    )

                dumped = data.model_dump(exclude_unset=True)
                only_status = set(dumped.keys()) <= {"status"}
                if only_status and "status" in dumped:
                    _require_perm(
                        session,
                        ctx.user,
                        "projectos.deactivate",
                        "Sem permissao para desactivar projectos.",
                    )
                else:
                    _require_manage(session, ctx.user)

                result = pilar_service.update_pilar(session, int(pilar_id), data)
                return api_json(app, {"pilar": result.model_dump(mode="json")})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
