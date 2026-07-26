"""Avaliacoes API — create + arquivo (list/detail) + anexos."""

from pydantic import ValidationError

from app.api.http import api_error, api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.models.enums import UserRole
from app.repositories import avaliacoes as aval_repo
from app.repositories import anexos as anexo_repo
from app.schemas.avaliacao import AvaliacaoCreate, AvaliacaoDetailOut, AvaliacaoListItem
from app.services import auth_service
from app.services.avaliacao_service import create_avaliacao
from app.services.anexo_service import create_for_avaliacao, serialize_anexo

API_PREFIX = "/api/v1"


def _body(request):
    body = request.body or {}
    if not isinstance(body, dict):
        return {}
    nested = body.get("body")
    if isinstance(nested, dict) and "pilar_id" in nested:
        return nested
    return body


def _extract_files(request) -> list:
    body = request.body or {}
    if not isinstance(body, dict):
        return []
    files = body.get("files") or body.get("file") or body.get("anexos") or []
    if files is None:
        return []
    if not isinstance(files, list):
        files = [files]
    return [f for f in files if getattr(f, "filename", None)]


def _list_item(row) -> dict:
    status = row.status.value if hasattr(row.status, "value") else (row.status or "submetida")
    return AvaliacaoListItem(
        id=row.id,
        pilar_id=row.pilar_id,
        pilar_nome=row.pilar.nome if row.pilar else "—",
        data_sub=row.data_sub,
        progresso=row.progresso or 0,
        estado_geral=(row.estado_geral or "")[:180],
        autor=row.user.name if row.user else None,
        status=status,
    ).model_dump(mode="json")


def _detail(row, session=None) -> dict:
    pilar = row.pilar
    act_names = {a.id: a.nome for a in (pilar.actividades if pilar else [])}
    cat_names = {c.id: c.categoria for c in (pilar.orcamento_categorias if pilar else [])}
    risco_map = {r.id: r for r in (pilar.riscos if pilar else [])}
    passo_map = {p.id: p for p in (pilar.proximos_passos if pilar else [])}
    status = row.status.value if hasattr(row.status, "value") else (row.status or "submetida")

    anexos = []
    if session is not None:
        anexos = [
            serialize_anexo(a)
            for a in anexo_repo.list_for_source(session, "avaliacao", row.id)
        ]

    return AvaliacaoDetailOut(
        id=row.id,
        pilar_id=row.pilar_id,
        pilar_nome=pilar.nome if pilar else "—",
        data_sub=row.data_sub,
        progresso=row.progresso or 0,
        autor=row.user.name if row.user else None,
        status=status,
        validation_note=row.validation_note,
        estado_geral=row.estado_geral or "",
        desafios=row.desafios or "",
        licoes=row.licoes or "",
        orc_obs=row.orc_obs,
        recomendacoes=row.recomendacoes,
        comentarios=row.comentarios,
        assinatura=row.assinatura,
        actividades=[
            {
                "pilar_actividade_id": a.pilar_actividade_id,
                "nome": act_names.get(a.pilar_actividade_id) or f"Actividade #{a.pilar_actividade_id}",
                "estado": a.estado.value if hasattr(a.estado, "value") else a.estado,
                "pct_conclusao": a.pct_conclusao,
                "data_inicio_real": a.data_inicio_real,
                "data_fim_real": a.data_fim_real,
                "obs_execucao": a.obs_execucao,
            }
            for a in row.actividades
        ],
        orcamentos=[
            {
                "categoria_id": o.categoria_id,
                "categoria": cat_names.get(o.categoria_id) or f"Rubrica #{o.categoria_id}",
                "valor_executado": o.valor_executado,
                "forma_execucao": o.forma_execucao,
                "obs": o.obs,
            }
            for o in row.orcamentos
        ],
        riscos=[
            {
                "risco_id": r.risco_id,
                "descricao": (
                    risco_map[r.risco_id].descricao
                    if r.risco_id in risco_map
                    else f"Risco #{r.risco_id}"
                ),
                "probabilidade": (
                    risco_map[r.risco_id].probabilidade.value
                    if r.risco_id in risco_map
                    and hasattr(risco_map[r.risco_id].probabilidade, "value")
                    else (
                        str(risco_map[r.risco_id].probabilidade)
                        if r.risco_id in risco_map
                        else None
                    )
                ),
                "impacto": (
                    risco_map[r.risco_id].impacto.value
                    if r.risco_id in risco_map and hasattr(risco_map[r.risco_id].impacto, "value")
                    else (str(risco_map[r.risco_id].impacto) if r.risco_id in risco_map else None)
                ),
                "mitigacao": risco_map[r.risco_id].mitigacao if r.risco_id in risco_map else None,
                "observacao": r.observacao,
            }
            for r in row.riscos
        ],
        proximos_passos=[
            {
                "passo_id": p.passo_id,
                "descricao": (
                    passo_map[p.passo_id].descricao
                    if p.passo_id in passo_map
                    else f"Passo #{p.passo_id}"
                ),
                "responsavel": passo_map[p.passo_id].responsavel if p.passo_id in passo_map else "",
                "prazo": passo_map[p.passo_id].prazo if p.passo_id in passo_map else None,
                "alcancado": p.alcancado,
                "observacao": p.observacao,
            }
            for p in row.proximos_passos
        ],
        anexos=anexos,
    ).model_dump(mode="json")


def register(app):
    @api_route(app, f"{API_PREFIX}/avaliacoes", methods=["GET", "POST"])
    def avaliacoes(request):
        method = (app.request.method if app.request else "GET").upper()
        try:
            with session_scope() as session:
                if method == "GET":
                    require_auth(app, session)
                    rows = aval_repo.list_avaliacoes(session)
                    return api_json(app, {"avaliacoes": [_list_item(r) for r in rows]})

                payload = AvaliacaoCreate.model_validate(_body(request))
                ctx = require_auth(app, session, UserRole.admin, UserRole.member)
                result = create_avaliacao(session, ctx.user, payload)
                return api_json(app, result.model_dump(mode="json"), status=201)
        except ValidationError as exc:
            return api_error(
                app,
                422,
                "VALIDATION_ERROR",
                "Dados da avaliacao invalidos.",
                details=exc.errors(include_url=False, include_context=False),
            )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/avaliacoes/{{avaliacao_id}}", methods=["GET", "PATCH"])
    def get_avaliacao(avaliacao_id, request=None):
        method = (app.request.method if app.request else "GET").upper()
        try:
            with session_scope() as session:
                if method == "GET":
                    require_auth(app, session)
                    row = aval_repo.get_by_id(session, int(avaliacao_id))
                    if not row:
                        return api_error(app, 404, "NOT_FOUND", "Avaliacao nao encontrada.")
                    return api_json(app, {"avaliacao": _detail(row, session)})

                ctx = require_auth(app, session, UserRole.admin, UserRole.member)
                try:
                    payload = AvaliacaoCreate.model_validate(_body(app.request))
                except ValidationError as exc:
                    return api_error(
                        app,
                        422,
                        "VALIDATION_ERROR",
                        "Dados da avaliacao invalidos.",
                        details=exc.errors(include_url=False, include_context=False),
                    )
                from app.services.avaliacao_service import update_avaliacao

                result = update_avaliacao(session, ctx.user, int(avaliacao_id), payload)
                return api_json(app, result.model_dump(mode="json"))
        except ValidationError as exc:
            return api_error(
                app,
                422,
                "VALIDATION_ERROR",
                "Dados da avaliacao invalidos.",
                details=exc.errors(include_url=False, include_context=False),
            )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/avaliacoes/{{avaliacao_id}}/validate", methods=["POST"])
    def validate_avaliacao_route(avaliacao_id, request=None):
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                body = _body(app.request) if app.request else {}
                note = body.get("validation_note") if isinstance(body, dict) else None
                from app.services.avaliacao_service import validate_avaliacao

                row = validate_avaliacao(session, ctx.user, int(avaliacao_id), note)
                row = aval_repo.get_by_id(session, row.id)
                return api_json(app, {"avaliacao": _detail(row, session), "message": "Avaliacao validada."})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/avaliacoes/{{avaliacao_id}}/reopen", methods=["POST"])
    def reopen_avaliacao_route(avaliacao_id, request=None):
        try:
            with session_scope() as session:
                ctx = require_auth(app, session)
                body = _body(app.request) if app.request else {}
                note = body.get("validation_note") if isinstance(body, dict) else None
                from app.services.avaliacao_service import reopen_avaliacao

                row = reopen_avaliacao(session, ctx.user, int(avaliacao_id), note)
                row = aval_repo.get_by_id(session, row.id)
                return api_json(app, {"avaliacao": _detail(row, session), "message": "Avaliacao reaberta."})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/avaliacoes/latest/{{pilar_id}}", methods=["GET"])
    def latest_avaliacao(pilar_id):
        try:
            with session_scope() as session:
                require_auth(app, session)
                row = aval_repo.get_latest_for_pilar(session, int(pilar_id))
                if not row:
                    return api_json(app, {"avaliacao": None})
                row = aval_repo.get_by_id(session, row.id)
                return api_json(app, {"avaliacao": _detail(row, session)})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/avaliacoes/{{avaliacao_id}}/anexos", methods=["POST"])
    def upload_avaliacao_anexos(request, avaliacao_id):
        try:
            with session_scope() as session:
                ctx = require_auth(app, session, UserRole.admin, UserRole.member)
                row = aval_repo.get_by_id(session, int(avaliacao_id))
                if not row:
                    return api_error(app, 404, "NOT_FOUND", "Avaliacao nao encontrada.")
                files = _extract_files(request)
                if not files:
                    return api_error(app, 422, "VALIDATION_ERROR", "Seleccione pelo menos um ficheiro.")
                created = create_for_avaliacao(session, ctx.user, row, files)
                return api_json(
                    app,
                    {"anexos": created, "message": f"{len(created)} anexo(s) carregado(s)."},
                    status=201,
                )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
        except Exception as exc:
            return api_error(app, 500, "UPLOAD_ERROR", str(exc))
