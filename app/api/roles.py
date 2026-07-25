"""Roles / permissions API."""

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.http import api_error, api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.models.enums import UserRole
from app.models.rbac import Permission, Role, RolePermission
from app.schemas.rbac import RoleCreate, RoleOut, RoleUpdate, PermissionOut
from app.services import auth_service
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


def _require_roles_manage(session, user) -> None:
    if user_has_permission(session, user, "roles.manage"):
        return
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role == UserRole.admin.value:
        return
    raise auth_service.AuthError("FORBIDDEN", "Sem permissao.", 403)


def _role_out(role: Role) -> dict:
    codes = [rp.permission.code for rp in role.permissions if rp.permission]
    data = RoleOut.model_validate(role).model_dump(mode="json")
    data["permission_codes"] = sorted(codes)
    return data


def _set_role_permissions(session, role: Role, codes: list[str]) -> None:
    perms = {
        p.code: p
        for p in session.scalars(select(Permission).where(Permission.code.in_(codes))).all()
    }
    existing = list(role.permissions)
    for rp in existing:
        session.delete(rp)
    session.flush()
    for code in codes:
        perm = perms.get(code)
        if perm:
            session.add(RolePermission(role_id=role.id, permission_id=perm.id))


def register(app):
    @api_route(app, f"{API_PREFIX}/permissions", methods=["GET"])
    def list_permissions():
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                _require_roles_manage(session, ctx.user)
                rows = session.scalars(
                    select(Permission).order_by(Permission.group_name, Permission.code)
                ).all()
                return api_json(
                    app,
                    {
                        "permissions": [
                            PermissionOut.model_validate(p).model_dump(mode="json") for p in rows
                        ]
                    },
                )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/roles", methods=["GET", "POST"])
    def roles(request):
        method = (app.request.method if app.request else "GET").upper()
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                if method == "GET":
                    # list roles: users.manage or roles.manage
                    if not (
                        user_has_permission(session, ctx.user, "roles.manage")
                        or user_has_permission(session, ctx.user, "users.manage")
                        or (
                            (ctx.user.role.value if hasattr(ctx.user.role, "value") else str(ctx.user.role))
                            == UserRole.admin.value
                        )
                    ):
                        raise auth_service.AuthError("FORBIDDEN", "Sem permissao.", 403)
                    rows = session.scalars(
                        select(Role)
                        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
                        .order_by(Role.name)
                    ).all()
                    return api_json(app, {"roles": [_role_out(r) for r in rows]})

                _require_roles_manage(session, ctx.user)
                try:
                    data = RoleCreate.model_validate(_body(request))
                except ValidationError as exc:
                    return api_error(
                        app,
                        422,
                        "VALIDATION_ERROR",
                        "Dados invalidos.",
                        details=exc.errors(include_url=False, include_context=False),
                    )
                if session.scalar(select(Role).where(Role.slug == data.slug)):
                    return api_error(app, 409, "SLUG_EXISTS", "Slug ja existe.")
                role = Role(
                    slug=data.slug,
                    name=data.name,
                    description=data.description or "",
                    is_system=False,
                )
                session.add(role)
                session.flush()
                _set_role_permissions(session, role, data.permission_codes)
                session.flush()
                role = session.scalar(
                    select(Role)
                    .where(Role.id == role.id)
                    .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
                )
                return api_json(app, {"role": _role_out(role)}, status=201)
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/roles/{{role_id}}", methods=["PATCH"])
    def update_role(role_id, request):
        try:
            data = RoleUpdate.model_validate(_body(request))
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
                _require_roles_manage(session, ctx.user)
                role = session.scalar(
                    select(Role)
                    .where(Role.id == int(role_id))
                    .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
                )
                if not role:
                    return api_error(app, 404, "NOT_FOUND", "Perfil nao encontrado.")
                if data.name is not None:
                    role.name = data.name
                if data.description is not None:
                    role.description = data.description
                if data.permission_codes is not None:
                    _set_role_permissions(session, role, data.permission_codes)
                session.flush()
                role = session.scalar(
                    select(Role)
                    .where(Role.id == role.id)
                    .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
                )
                return api_json(app, {"role": _role_out(role)})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
