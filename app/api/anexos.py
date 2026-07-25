"""Anexos API — listagem global + download."""

from __future__ import annotations

from urllib.parse import quote

from pyweber.models.response import Response
from pyweber.utils.types import ContentTypes

from app.api.http import api_error, api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.repositories import anexos as anexo_repo
from app.services import auth_service, storage
from app.services.anexo_service import list_anexos, serialize_anexo

API_PREFIX = "/api/v1"


def _query_int(request, key: str, default: int) -> int:
    raw = (request.query_params or {}).get(key)
    try:
        return int(raw) if raw is not None and str(raw).strip() != "" else default
    except (TypeError, ValueError):
        return default


def _query_str(request, key: str, default: str = "") -> str:
    raw = (request.query_params or {}).get(key)
    return str(raw).strip() if raw is not None else default


def register(app) -> None:
    @api_route(app, f"{API_PREFIX}/anexos", methods=["GET"])
    def anexos_list(request):
        try:
            with session_scope() as session:
                require_auth(app, session)
                page = _query_int(request, "page", 1)
                page_size = _query_int(request, "page_size", 20)
                q = _query_str(request, "q", "")
                source_type = _query_str(request, "source_type", "") or None
                data = list_anexos(
                    session,
                    q=q,
                    page=page,
                    page_size=page_size,
                    source_type=source_type,
                )
                return api_json(app, data)
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/anexos/{{anexo_id}}", methods=["GET"])
    def anexo_detail(anexo_id):
        try:
            with session_scope() as session:
                require_auth(app, session)
                row = anexo_repo.get_by_id(session, int(anexo_id))
                if not row:
                    return api_error(app, 404, "NOT_FOUND", "Anexo nao encontrado.")
                return api_json(app, {"anexo": serialize_anexo(row)})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/anexos/{{anexo_id}}/download", methods=["GET"])
    def anexo_download(anexo_id):
        try:
            with session_scope() as session:
                require_auth(app, session)
                row = anexo_repo.get_by_id(session, int(anexo_id))
                if not row:
                    return api_error(app, 404, "NOT_FOUND", "Anexo nao encontrado.")
                try:
                    data = storage.read_bytes(row.storage_key)
                except FileNotFoundError:
                    return api_error(app, 404, "NOT_FOUND", "Ficheiro em falta no armazenamento.")
                except Exception as exc:
                    return api_error(app, 500, "STORAGE_ERROR", f"Erro ao ler ficheiro: {exc}")

                ctype = row.content_type or ContentTypes.unkown.value
                # Prefer known ContentTypes enum if possible
                try:
                    response_type = ContentTypes(ctype)
                except ValueError:
                    response_type = ContentTypes.unkown

                resp = Response(
                    request=app.request,
                    response_content=data,
                    code=200,
                    cookies=dict(app.cookies),
                    response_type=response_type,
                    route=app.request.path if app.request else "/",
                )
                resp.update_header("Content-Type", ctype)
                fname = quote(row.original_name or "anexo")
                resp.set_header(
                    "Content-Disposition",
                    f"attachment; filename=\"{row.original_name}\"; filename*=UTF-8''{fname}",
                )
                resp.headers.pop("WWW-Authenticate", None)
                return resp
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
        except Exception as exc:
            return api_error(app, 500, "DOWNLOAD_ERROR", str(exc))
