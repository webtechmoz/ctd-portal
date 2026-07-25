"""Users API — admin (GET+POST same path — pyweber forbids duplicate paths)."""

from pydantic import ValidationError
from sqlalchemy import select

from app.api.http import api_error, api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.models.enums import UserRole
from app.models.rbac import Role
from app.repositories import users as user_repo
from app.schemas.users import UserCreate, UserUpdate
from app.services import auth_service
from app.services.rbac_service import sync_user_enum_from_role, user_has_permission
from app.services.user_serialize import user_to_public
from config.settings import settings

API_PREFIX = "/api/v1"


def _body(request):
    body = getattr(request, "body", None) or {}
    if not isinstance(body, dict):
        return {}
    nested = body.get("body")
    if isinstance(nested, dict):
        return nested
    return body


def _require_users_perm(session, user, code: str) -> None:
    if user_has_permission(session, user, code):
        return
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role == UserRole.admin.value:
        return
    raise auth_service.AuthError("FORBIDDEN", "Sem permissao.", 403)


def register(app):
    @api_route(app, f"{API_PREFIX}/users", methods=["GET", "POST"])
    def users(request):
        method = (app.request.method if app.request else "GET").upper()
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                if method == "GET":
                    _require_users_perm(session, ctx.user, "users.view")
                    rows = user_repo.list_users(session)
                    return api_json(
                        app,
                        {"users": [user_to_public(session, u) for u in rows]},
                    )

                _require_users_perm(session, ctx.user, "users.manage")
                try:
                    data = UserCreate.model_validate(_body(request))
                except ValidationError as exc:
                    return api_error(
                        app,
                        422,
                        "VALIDATION_ERROR",
                        "Dados invalidos.",
                        details=exc.errors(include_url=False, include_context=False),
                    )
                email = str(data.email).lower().strip()
                domain = settings.ALLOWED_EMAIL_DOMAIN.lower().lstrip("@")
                if not email.endswith(f"@{domain}"):
                    return api_error(app, 422, "INVALID_EMAIL_DOMAIN", "Email deve ser institucional.")
                if user_repo.get_by_email(session, email):
                    return api_error(app, 409, "EMAIL_EXISTS", "Email ja registado.")

                role_id = data.role_id
                role_enum = data.role or UserRole.member
                if role_id:
                    role_row = session.get(Role, role_id)
                    if not role_row:
                        return api_error(app, 422, "INVALID_ROLE", "Perfil invalido.")
                    try:
                        role_enum = UserRole(role_row.slug)
                    except ValueError:
                        role_enum = UserRole.member
                else:
                    role_row = session.scalar(select(Role).where(Role.slug == role_enum.value))
                    role_id = role_row.id if role_row else None

                user = user_repo.create_user(
                    session,
                    name=data.name,
                    email=email,
                    password_hash=auth_service.hash_password(data.password),
                    role=role_enum,
                )
                user.role_id = role_id
                session.flush()
                return api_json(app, {"user": user_to_public(session, user)}, status=201)
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/users/{{user_id}}", methods=["PATCH"])
    def update_user(user_id, request):
        try:
            data = UserUpdate.model_validate(_body(request))
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
                _require_users_perm(session, ctx.user, "users.manage")
                user = user_repo.get_by_id(session, int(user_id))
                if not user:
                    return api_error(app, 404, "NOT_FOUND", "Utilizador nao encontrado.")
                if data.name is not None:
                    user.name = data.name.strip()
                if data.status is not None:
                    user.status = data.status
                if data.role_id is not None:
                    user.role_id = data.role_id
                    sync_user_enum_from_role(session, user)
                elif data.role is not None:
                    user.role = data.role
                    role_row = session.scalar(select(Role).where(Role.slug == data.role.value))
                    if role_row:
                        user.role_id = role_row.id
                session.flush()
                return api_json(app, {"user": user_to_public(session, user)})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
