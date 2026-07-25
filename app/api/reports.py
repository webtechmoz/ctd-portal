"""Reports / overview API — global portfolio KPIs."""

from datetime import date
from decimal import Decimal

from app.api.http import api_json, api_route
from app.db.session_scope import session_scope
from app.middleware.auth import handle_auth_error, require_auth
from app.repositories import pilares as pilar_repo
from app.services import auth_service
from app.services.dashboard_service import build_dashboard

API_PREFIX = "/api/v1"


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
