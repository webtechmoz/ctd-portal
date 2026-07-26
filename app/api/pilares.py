"""Pilares API — list / detail / create / update + Excel import/export."""

from urllib.parse import quote

from pydantic import ValidationError
from pyweber.models.response import Response
from pyweber.utils.types import ContentTypes

from app.api.http import api_error, api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.models.enums import UserRole
from app.repositories import pilares as pilar_repo
from app.schemas.pilar import PilarListItem, PilarUpdate, PilarWrite
from app.services import auth_service
from app.services import pilar_service
from app.services.excel_io import (
    build_import_template,
    export_pilares,
    import_pilares_from_xlsx,
)
from app.services.rbac_service import user_has_permission

API_PREFIX = "/api/v1"
XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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


def _query_str(request, key: str, default: str = "") -> str:
    raw = (request.query_params or {}).get(key) if request else None
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else default
    return str(raw or default).strip()


def _extract_files(request) -> list:
    body = getattr(request, "body", None) or {}
    if not isinstance(body, dict):
        return []
    files = body.get("files") or body.get("file") or []
    if files is None:
        return []
    if not isinstance(files, list):
        files = [files]
    return [f for f in files if getattr(f, "filename", None)]


def _xlsx_response(app, data: bytes, filename: str) -> Response:
    resp = Response(
        request=app.request,
        response_content=data,
        code=200,
        cookies=dict(app.cookies),
        response_type=ContentTypes.unkown,
        route=app.request.path if app.request else "/",
    )
    resp.update_header("Content-Type", XLSX_CT)
    fname = quote(filename)
    resp.set_header(
        "Content-Disposition",
        f'attachment; filename="{filename}"; filename*=UTF-8\'\'{fname}',
    )
    resp.headers.pop("WWW-Authenticate", None)
    return resp


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

    @api_route(app, f"{API_PREFIX}/pilares/export.xlsx", methods=["GET"])
    def pilares_export(request):
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                _require_manage(session, ctx.user)
                ids_raw = _query_str(request, "ids")
                pilar_ids = None
                if ids_raw:
                    pilar_ids = []
                    for part in ids_raw.split(","):
                        part = part.strip()
                        if part.isdigit():
                            pilar_ids.append(int(part))
                data = export_pilares(session, pilar_ids)
                return _xlsx_response(app, data, "projectos-export.xlsx")
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
        except Exception as exc:
            return api_error(app, 500, "EXPORT_ERROR", str(exc))

    @api_route(app, f"{API_PREFIX}/pilares/import-template.xlsx", methods=["GET"])
    def pilares_import_template():
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                _require_manage(session, ctx.user)
                data = build_import_template(session)
                return _xlsx_response(app, data, "projectos-modelo.xlsx")
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/pilares/import", methods=["POST"])
    def pilares_import(request):
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                _require_manage(session, ctx.user)
                files = _extract_files(request)
                if not files:
                    return api_error(app, 422, "VALIDATION_ERROR", "Seleccione um ficheiro .xlsx.")
                raw = files[0]
                data = getattr(raw, "content", None) or b""
                if isinstance(data, str):
                    data = data.encode("latin-1")
                if not isinstance(data, (bytes, bytearray)) or not data:
                    return api_error(app, 422, "VALIDATION_ERROR", "Ficheiro invalido ou vazio.")
                dry = _query_str(request, "dry_run") in ("1", "true", "yes")
                result = import_pilares_from_xlsx(session, bytes(data), dry_run=dry)
                status = 200 if result.get("ok") or dry else 422
                return api_json(app, result, status=status)
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
        except Exception as exc:
            return api_error(app, 500, "IMPORT_ERROR", str(exc))

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
                        {
                            "pilar": pilar_service.master_out(session, pilar).model_dump(
                                mode="json"
                            )
                        },
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
