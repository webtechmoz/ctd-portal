"""Catalog API — listas de sistema."""

from pydantic import BaseModel, Field, ValidationError

from app.api.http import api_error, api_json, api_route
from app.catalog_seed import CATALOG_LABELS
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.models.enums import UserRole
from app.services import auth_service, catalog_service
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
    if user_has_permission(session, user, "catalog.manage"):
        return
    # Back-compat: profiles that already had admin/project manage
    if user_has_permission(session, user, "admin.access") or user_has_permission(
        session, user, "projectos.manage"
    ):
        return
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role == UserRole.admin.value:
        return
    raise auth_service.AuthError("FORBIDDEN", "Sem permissao.", 403)


def _serialize(opt, session=None) -> dict:
    data = {
        "id": opt.id,
        "category": opt.category,
        "code": opt.code,
        "label": opt.label,
        "sort_order": opt.sort_order,
        "is_system": opt.is_system,
        "active": opt.active,
    }
    if session is not None:
        data["in_use"] = catalog_service.option_in_use(session, opt)
    return data


class CatalogCreate(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=150)


class CatalogUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=150)
    active: bool | None = None


def register(app):
    @api_route(app, f"{API_PREFIX}/catalog", methods=["GET", "POST"])
    def catalog(request):
        method = (app.request.method if app.request else "GET").upper()
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                if method == "GET":
                    rows = catalog_service.list_all(session)
                    grouped: dict[str, list] = {}
                    for opt in rows:
                        grouped.setdefault(opt.category, []).append(_serialize(opt, session))
                    return api_json(
                        app,
                        {
                            "categories": CATALOG_LABELS,
                            "options": grouped,
                        },
                    )

                _require_manage(session, ctx.user)
                try:
                    data = CatalogCreate.model_validate(_body(request))
                except ValidationError as exc:
                    return api_error(
                        app,
                        422,
                        "VALIDATION_ERROR",
                        "Dados invalidos.",
                        details=exc.errors(include_url=False, include_context=False),
                    )
                if data.category not in CATALOG_LABELS:
                    return api_error(app, 422, "VALIDATION_ERROR", "Categoria desconhecida.")
                opt = catalog_service.create_option(
                    session, category=data.category, code=data.code, label=data.label
                )
                return api_json(app, {"option": _serialize(opt, session)}, status=201)
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/catalog/{{category}}", methods=["GET"])
    def catalog_category(category):
        try:
            with session_scope() as session:
                require_auth(app, session)
                rows = catalog_service.list_by_category(session, category, active_only=True)
                return api_json(
                    app,
                    {
                        "category": category,
                        "label": CATALOG_LABELS.get(category, category),
                        "options": [_serialize(o) for o in rows],
                    },
                )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/catalog/item/{{opt_id}}", methods=["PATCH", "DELETE"])
    def catalog_item(opt_id):
        method = (app.request.method if app.request else "PATCH").upper()
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                _require_manage(session, ctx.user)
                if method == "DELETE":
                    catalog_service.delete_option(session, int(opt_id))
                    return api_json(app, {"ok": True})
                try:
                    data = CatalogUpdate.model_validate(_body(app.request))
                except ValidationError as exc:
                    return api_error(
                        app,
                        422,
                        "VALIDATION_ERROR",
                        "Dados invalidos.",
                        details=exc.errors(include_url=False, include_context=False),
                    )
                opt = catalog_service.update_option(
                    session,
                    int(opt_id),
                    label=data.label,
                    active=data.active,
                )
                return api_json(app, {"option": _serialize(opt, session)})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
