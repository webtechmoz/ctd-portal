"""Auth API routes."""

from pydantic import ValidationError

from app.api.http import api_error, api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.schemas.auth import ChangePasswordRequest, LoginRequest, MessageResponse
from app.services import auth_service
from app.services.rbac_service import user_has_permission
from app.services.user_serialize import user_to_public

API_PREFIX = "/api/v1"


def _extract_body(request):
    body = request.body or {}
    if not isinstance(body, dict):
        return {}
    nested = body.get("body")
    if isinstance(nested, dict) and (
        "email" in nested
        or "password" in nested
        or "current_password" in nested
        or "new_password" in nested
    ):
        return nested
    return body


def register(app):
    @api_route(app, f"{API_PREFIX}/auth/login", methods=["POST"])
    def login(request):
        try:
            data = LoginRequest.model_validate(_extract_body(request))
        except ValidationError as exc:
            return api_error(
                app,
                422,
                "VALIDATION_ERROR",
                "Dados de login invalidos.",
                details=exc.errors(include_url=False, include_context=False),
            )

        try:
            with session_scope() as session:
                user, token, _expires = auth_service.login(
                    session, str(data.email), data.password
                )
                public = user_to_public(session, user)
                auth_service.set_auth_cookie(app, token)
                return api_json(app, {"user": public}, status=200)
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
        except RuntimeError as exc:
            return api_error(app, 500, "DB_NOT_READY", str(exc))

    @api_route(app, f"{API_PREFIX}/auth/logout", methods=["POST"])
    def logout():
        token = auth_service.read_access_token(app)
        try:
            with session_scope() as session:
                auth_service.logout(session, token)
        except Exception:
            pass
        auth_service.clear_auth_cookie(app)
        return api_json(
            app,
            MessageResponse(message="Sessao terminada.").model_dump(),
        )

    @api_route(app, f"{API_PREFIX}/auth/me", methods=["GET"])
    def me():
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                public = user_to_public(session, ctx.user)
                return api_json(app, {"user": public})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/auth/password", methods=["PATCH"])
    def change_password(request):
        try:
            data = ChangePasswordRequest.model_validate(_extract_body(request))
        except ValidationError as exc:
            return api_error(
                app,
                422,
                "VALIDATION_ERROR",
                "Dados invalidos.",
                details=exc.errors(include_url=False, include_context=False),
            )
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                if not user_has_permission(session, ctx.user, "account.change_password"):
                    raise auth_service.AuthError(
                        "FORBIDDEN", "Sem permissao para alterar a palavra-passe.", 403
                    )
                if not auth_service.verify_password(
                    data.current_password, ctx.user.password_hash
                ):
                    return api_error(
                        app, 400, "INVALID_PASSWORD", "Palavra-passe actual incorrecta."
                    )
                ctx.user.password_hash = auth_service.hash_password(data.new_password)
                ctx.user.must_change_password = False
                session.add(ctx.user)
                return api_json(
                    app,
                    MessageResponse(message="Palavra-passe actualizada.").model_dump(),
                )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
