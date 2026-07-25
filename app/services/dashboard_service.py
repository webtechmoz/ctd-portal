"""Dashboard assembly service."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import ActividadeEstado, Impacto, Probabilidade
from app.models.pilar import Pilar
from app.repositories import avaliacoes as avaliacao_repo
from app.repositories import pilares as pilar_repo
from app.schemas.dashboard import (
    DashActividade,
    DashOrcamento,
    DashPasso,
    DashResumo,
    DashRisco,
    DashboardResponse,
)
from app.schemas.pilar import PilarDetail
from app.services import auth_service


def build_dashboard(session: Session, pilar_id: int) -> DashboardResponse:
    pilar = pilar_repo.get_with_master(session, pilar_id)
    if not pilar:
        raise auth_service.AuthError("NOT_FOUND", "Pilar nao encontrado.", 404)

    latest = avaliacao_repo.get_latest_for_pilar(session, pilar_id)
    pilar_detail = PilarDetail.model_validate(pilar)
    objectivos = [o.descricao for o in sorted(pilar.objectivos, key=lambda x: x.ordem)]

    if not latest:
        return DashboardResponse(
            pilar=pilar_detail,
            tem_avaliacao=False,
            resumo=DashResumo(),
            objectivos=objectivos,
        )

    act_by_id = {a.id: a for a in pilar.actividades}
    cat_by_id = {c.id: c for c in pilar.orcamento_categorias}
    risco_by_id = {r.id: r for r in pilar.riscos}
    passo_by_id = {p.id: p for p in pilar.proximos_passos}

    actividades: list[DashActividade] = []
    concluidas = em_prog = pendentes = 0
    for row in latest.actividades:
        base = act_by_id.get(row.pilar_actividade_id)
        estado = row.estado.value if hasattr(row.estado, "value") else str(row.estado)
        if estado == ActividadeEstado.concluida.value:
            concluidas += 1
        elif estado == ActividadeEstado.em_progresso.value:
            em_prog += 1
        else:
            pendentes += 1
        actividades.append(
            DashActividade(
                nome=base.nome if base else f"#{row.pilar_actividade_id}",
                responsavel=base.responsavel if base else "",
                estado=estado,
                pct_conclusao=row.pct_conclusao,
                prioridade=(
                    base.prioridade.value
                    if base and hasattr(base.prioridade, "value")
                    else (str(base.prioridade) if base else "media")
                ),
            )
        )

    orcamentos: list[DashOrcamento] = []
    alocado_total = Decimal("0")
    executado_total = Decimal("0")
    for row in latest.orcamentos:
        cat = cat_by_id.get(row.categoria_id)
        alocado = cat.valor_alocado if cat else Decimal("0")
        alocado_total += alocado
        executado_total += row.valor_executado or Decimal("0")
        orcamentos.append(
            DashOrcamento(
                categoria=cat.categoria if cat else f"#{row.categoria_id}",
                valor_alocado=alocado,
                valor_executado=row.valor_executado or Decimal("0"),
            )
        )

    riscos: list[DashRisco] = []
    riscos_altos = 0
    for row in latest.riscos:
        base = risco_by_id.get(row.risco_id)
        prob = (
            base.probabilidade.value
            if base and hasattr(base.probabilidade, "value")
            else (str(base.probabilidade) if base else "media")
        )
        impacto = (
            base.impacto.value
            if base and hasattr(base.impacto, "value")
            else (str(base.impacto) if base else "medio")
        )
        if prob == Probabilidade.alta.value or impacto == Impacto.alto.value:
            riscos_altos += 1
        riscos.append(
            DashRisco(
                descricao=base.descricao if base else "",
                probabilidade=prob,
                impacto=impacto,
                mitigacao=base.mitigacao if base else None,
                observacao=row.observacao,
            )
        )

    passos: list[DashPasso] = []
    for row in latest.proximos_passos:
        base = passo_by_id.get(row.passo_id)
        passos.append(
            DashPasso(
                descricao=base.descricao if base else "",
                responsavel=base.responsavel if base else "",
                prazo=base.prazo if base else None,
                alcancado=row.alcancado,
            )
        )

    total_acts = len(actividades)
    orc_pct = float((executado_total / alocado_total) * 100) if alocado_total else 0.0

    resumo = DashResumo(
        progresso=float(latest.progresso or 0),
        orcamento_pct=round(orc_pct, 1),
        actividades_total=total_acts,
        actividades_concluidas=concluidas,
        actividades_em_progresso=em_prog,
        actividades_pendentes=pendentes,
        riscos_altos=riscos_altos,
    )

    return DashboardResponse(
        pilar=pilar_detail,
        tem_avaliacao=True,
        avaliacao_id=latest.id,
        data_sub=latest.data_sub,
        estado_geral=latest.estado_geral,
        desafios=latest.desafios,
        licoes=latest.licoes,
        recomendacoes=latest.recomendacoes,
        comentarios=latest.comentarios,
        progresso=float(latest.progresso or 0),
        resumo=resumo,
        objectivos=objectivos,
        actividades=actividades,
        orcamentos=orcamentos,
        riscos=riscos,
        proximos_passos=passos,
    )
