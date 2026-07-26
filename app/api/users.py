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
from app.services.email_service import send_credentials_email
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


def _is_seed_admin(email: str) -> bool:
    return email.strip().lower() == settings.SEED_ADMIN_EMAIL.strip().lower()


def _login_url() -> str:
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    base = origins[0] if origins else f"http://localhost:{settings.bind_port}"
    return f"{base.rstrip('/')}/login"


def register(app):
    @api_route(app, f"{API_PREFIX}/users/options", methods=["GET"])
    def users_options():
        """Lista leve de utilizadores activos para selects (responsavel do projecto)."""
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                from app.models.enums import UserStatus

                can = user_has_permission(session, ctx.user, "users.view") or user_has_permission(
                    session, ctx.user, "projectos.manage"
                )
                role = ctx.user.role.value if hasattr(ctx.user.role, "value") else str(ctx.user.role)
                if not can and role != UserRole.admin.value:
                    raise auth_service.AuthError("FORBIDDEN", "Sem permissao.", 403)
                rows = user_repo.list_users(session, status=UserStatus.active)
                return api_json(
                    app,
                    {
                        "users": [
                            {
                                "id": u.id,
                                "name": u.name,
                                "email": u.email,
                                "role": u.role.value if hasattr(u.role, "value") else str(u.role),
                            }
                            for u in rows
                        ]
                    },
                )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

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
                if not settings.email_domain_allowed(email):
                    allowed = ", ".join(settings.allowed_email_domains)
                    return api_error(
                        app,
                        422,
                        "INVALID_EMAIL_DOMAIN",
                        f"Email fora dos dominios permitidos ({allowed}).",
                    )
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

                force_pw = not _is_seed_admin(email)
                plain_password = data.password
                if data.send_credentials and not plain_password:
                    plain_password = auth_service.generate_temp_password()
                if not plain_password:
                    return api_error(
                        app,
                        422,
                        "VALIDATION_ERROR",
                        "Password obrigatoria ou active o envio de credenciais.",
                    )

                user = user_repo.create_user(
                    session,
                    name=data.name,
                    email=email,
                    password_hash=auth_service.hash_password(plain_password),
                    role=role_enum,
                    must_change_password=force_pw,
                )
                user.role_id = role_id
                session.flush()

                email_sent = False
                if data.send_credentials:
                    email_sent = send_credentials_email(
                        name=user.name,
                        email=user.email,
                        password=plain_password,
                        login_url=_login_url(),
                    )

                return api_json(
                    app,
                    {
                        "user": user_to_public(session, user),
                        "credentials_email_sent": email_sent,
                    },
                    status=201,
                )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/users/{{user_id}}/send-credentials", methods=["POST"])
    def send_user_credentials(user_id):
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                _require_users_perm(session, ctx.user, "users.manage")
                user = user_repo.get_by_id(session, int(user_id))
                if not user:
                    return api_error(app, 404, "NOT_FOUND", "Utilizador nao encontrado.")
                plain = auth_service.generate_temp_password()
                user.password_hash = auth_service.hash_password(plain)
                if not _is_seed_admin(user.email):
                    user.must_change_password = True
                session.flush()
                email_sent = send_credentials_email(
                    name=user.name,
                    email=user.email,
                    password=plain,
                    login_url=_login_url(),
                    reset=True,
                )
                return api_json(
                    app,
                    {
                        "ok": True,
                        "credentials_email_sent": email_sent,
                        "user": user_to_public(session, user),
                    },
                )
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

                email_sent = False
                if data.password:
                    user.password_hash = auth_service.hash_password(data.password)
                    if not _is_seed_admin(user.email):
                        user.must_change_password = True
                    if data.send_credentials:
                        email_sent = send_credentials_email(
                            name=user.name,
                            email=user.email,
                            password=data.password,
                            login_url=_login_url(),
                            reset=True,
                        )

                session.flush()
                payload = {"user": user_to_public(session, user)}
                if data.password is not None:
                    payload["credentials_email_sent"] = email_sent
                return api_json(app, payload)
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
