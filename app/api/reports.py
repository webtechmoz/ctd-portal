"""Reports / overview API — global portfolio KPIs + avaliacoes."""

from datetime import date
from decimal import Decimal
from urllib.parse import quote

from pyweber.models.response import Response
from pyweber.utils.types import ContentTypes

from app.api.http import api_error, api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.repositories import pilares as pilar_repo
from app.services import auth_service
from app.services.dashboard_service import build_dashboard
from app.services.excel_io import build_avaliacoes_report, list_avaliacoes_report

API_PREFIX = "/api/v1"
XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _query_str(request, key: str, default: str = "") -> str:
    raw = (request.query_params or {}).get(key) if request else None
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else default
    return str(raw or default).strip()


def _query_date(request, key: str) -> date | None:
    raw = _query_str(request, key)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _query_int(request, key: str) -> int | None:
    raw = _query_str(request, key)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


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
    @api_route(app, f"{API_PREFIX}/reports/overview", methods=["GET"])
    def overview():
        try:
            with session_scope() as session:
                require_auth(app, session)
                pilares = pilar_repo.list_activos(session)
                today = date.today()
                items = []
                progresso_vals = []
                orc_vals = []
                atraso = breve = ok = sem_data = 0
                orc_aprovado_total = Decimal("0")
                orc_executado_total = Decimal("0")

                for p in pilares:
                    dash = build_dashboard(session, p.id)
                    progresso = dash.resumo.progresso if dash.tem_avaliacao else 0
                    orc = dash.resumo.orcamento_pct if dash.tem_avaliacao else 0
                    aprovado = Decimal(str(p.orc_aprovado or 0))
                    orc_aprovado_total += aprovado
                    exec_p = Decimal("0")
                    if dash.tem_avaliacao:
                        progresso_vals.append(progresso)
                        orc_vals.append(orc)
                        for o in dash.orcamentos:
                            exec_p += Decimal(str(o.valor_executado or 0))
                        orc_executado_total += exec_p

                    days = None
                    if p.proxima_avaliacao:
                        days = (p.proxima_avaliacao - today).days
                        if days < 0:
                            atraso += 1
                            situacao = "atraso"
                        elif days <= 7:
                            breve += 1
                            situacao = "breve"
                        else:
                            ok += 1
                            situacao = "ok"
                    else:
                        sem_data += 1
                        situacao = "sem_data"

                    items.append(
                        {
                            "id": p.id,
                            "nome": p.nome,
                            "area": p.area,
                            "fase": p.fase,
                            "orc_aprovado": float(aprovado),
                            "orc_moeda": p.orc_moeda or "MZN",
                            "proxima_avaliacao": p.proxima_avaliacao.isoformat()
                            if p.proxima_avaliacao
                            else None,
                            "dias": days,
                            "situacao": situacao,
                            "tem_avaliacao": dash.tem_avaliacao,
                            "progresso": progresso,
                            "orcamento_pct": orc,
                            "riscos_altos": dash.resumo.riscos_altos if dash.tem_avaliacao else 0,
                            "actividades_concluidas": dash.resumo.actividades_concluidas
                            if dash.tem_avaliacao
                            else 0,
                            "actividades_total": dash.resumo.actividades_total
                            if dash.tem_avaliacao
                            else 0,
                        }
                    )

                avg_prog = (
                    round(sum(progresso_vals) / len(progresso_vals), 1) if progresso_vals else 0
                )
                avg_orc = round(sum(orc_vals) / len(orc_vals), 1) if orc_vals else 0
                orc_pct_global = (
                    float((orc_executado_total / orc_aprovado_total) * 100)
                    if orc_aprovado_total
                    else 0.0
                )

                return api_json(
                    app,
                    {
                        "resumo": {
                            "projectos": len(pilares),
                            "com_avaliacao": len(progresso_vals),
                            "progresso_medio": avg_prog,
                            "orcamento_medio": avg_orc,
                            "orcamento_aprovado_total": float(orc_aprovado_total),
                            "orcamento_executado_total": float(orc_executado_total),
                            "orcamento_pct_global": round(orc_pct_global, 1),
                            "atraso": atraso,
                            "breve": breve,
                            "ok": ok,
                            "sem_data": sem_data,
                        },
                        "pilares": items,
                    },
                )
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/reports/avaliacoes", methods=["GET"])
    def reports_avaliacoes(request):
        try:
            with session_scope() as session:
                require_auth(app, session)
                items = list_avaliacoes_report(
                    session,
                    pilar_id=_query_int(request, "pilar_id"),
                    status=_query_str(request, "status") or None,
                    date_from=_query_date(request, "from"),
                    date_to=_query_date(request, "to"),
                )
                return api_json(app, {"avaliacoes": items, "total": len(items)})
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)

    @api_route(app, f"{API_PREFIX}/reports/avaliacoes/export.xlsx", methods=["GET"])
    def reports_avaliacoes_export(request):
        try:
            with session_scope() as session:
                require_auth(app, session)
                data = build_avaliacoes_report(
                    session,
                    pilar_id=_query_int(request, "pilar_id"),
                    status=_query_str(request, "status") or None,
                    date_from=_query_date(request, "from"),
                    date_to=_query_date(request, "to"),
                )
                return _xlsx_response(app, data, "relatorio-avaliacoes.xlsx")
        except auth_service.AuthError as exc:
            return handle_auth_error(app, exc)
        except Exception as exc:
            return api_error(app, 500, "EXPORT_ERROR", str(exc))
