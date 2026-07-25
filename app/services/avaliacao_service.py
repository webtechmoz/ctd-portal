"""Avaliacao create service — transactional deltas + scheduling."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.avaliacao import (
    Avaliacao,
    AvaliacaoActividade,
    AvaliacaoOrcamento,
    AvaliacaoProximoPasso,
    AvaliacaoRisco,
)
from app.models.enums import ActividadeEstado, UserRole
from app.models.pilar import Pilar, PilarProximoPasso, PilarResponsavel
from app.models.user import User
from app.repositories import avaliacoes as aval_repo
from app.repositories import pilares as pilar_repo
from app.schemas.avaliacao import AvaliacaoCreate, AvaliacaoCreated
from app.services import auth_service


def user_can_evaluate(session: Session, user: User, pilar_id: int) -> bool:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role == UserRole.admin.value:
        return True
    if role != UserRole.member.value:
        return False
    link = session.scalar(
        select(PilarResponsavel).where(
            PilarResponsavel.pilar_id == pilar_id,
            PilarResponsavel.user_id == user.id,
        )
    )
    return link is not None


def _estado_from_pct(pct: int) -> ActividadeEstado:
    if pct >= 100:
        return ActividadeEstado.concluida
    if pct > 0:
        return ActividadeEstado.em_progresso
    return ActividadeEstado.pendente


def create_avaliacao(session: Session, user: User, payload: AvaliacaoCreate) -> AvaliacaoCreated:
    pilar = pilar_repo.get_with_master(session, payload.pilar_id)
    if not pilar:
        raise auth_service.AuthError("NOT_FOUND", "Pilar nao encontrado.", 404)

    if not user_can_evaluate(session, user, pilar.id):
        raise auth_service.AuthError(
            "FORBIDDEN",
            "Nao tem permissao para avaliar este pilar.",
            403,
        )

    previous = aval_repo.get_latest_for_pilar(session, pilar.id)
    prev_act = {
        a.pilar_actividade_id: a for a in (previous.actividades if previous else [])
    }
    prev_orc = {o.categoria_id: o for o in (previous.orcamentos if previous else [])}

    act_ids = {a.id for a in pilar.actividades}
    cat_ids = {c.id for c in pilar.orcamento_categorias}
    risco_ids = {r.id for r in pilar.riscos}
    passo_ids = {p.id for p in pilar.proximos_passos}

    for row in payload.actividades:
        if row.pilar_actividade_id not in act_ids:
            raise auth_service.AuthError(
                "VALIDATION_ERROR",
                f"Actividade {row.pilar_actividade_id} nao pertence ao pilar.",
                422,
            )
        prev = prev_act.get(row.pilar_actividade_id)
        min_pct = int(prev.pct_conclusao) if prev else 0
        if row.pct_conclusao < min_pct:
            raise auth_service.AuthError(
                "VALIDATION_ERROR",
                f"% conclusao nao pode ser inferior a {min_pct}% (avaliacao anterior).",
                422,
            )

    for row in payload.orcamentos:
        if row.categoria_id not in cat_ids:
            raise auth_service.AuthError(
                "VALIDATION_ERROR",
                f"Categoria {row.categoria_id} nao pertence ao pilar.",
                422,
            )
        prev = prev_orc.get(row.categoria_id)
        min_val = Decimal(prev.valor_executado) if prev else Decimal("0")
        if Decimal(row.valor_executado) < min_val:
            raise auth_service.AuthError(
                "VALIDATION_ERROR",
                f"Valor executado nao pode ser inferior a {min_val} (avaliacao anterior).",
                422,
            )

    for row in payload.riscos:
        if row.risco_id not in risco_ids:
            raise auth_service.AuthError(
                "VALIDATION_ERROR",
                f"Risco {row.risco_id} nao pertence ao pilar.",
                422,
            )

    resolved_passos: list[tuple[int, bool, str | None]] = []
    next_ordem = len(pilar.proximos_passos)
    for row in payload.proximos_passos:
        if row.passo_id is not None:
            if row.passo_id not in passo_ids:
                raise auth_service.AuthError(
                    "VALIDATION_ERROR",
                    f"Passo {row.passo_id} nao pertence ao pilar.",
                    422,
                )
            resolved_passos.append((row.passo_id, row.alcancado, row.observacao))
            continue
        desc = (row.descricao or "").strip()
        if not desc:
            raise auth_service.AuthError(
                "VALIDATION_ERROR",
                "Proximos passos novos precisam de descricao.",
                422,
            )
        novo = PilarProximoPasso(
            pilar_id=pilar.id,
            descricao=desc,
            responsavel=(row.responsavel or "").strip(),
            prazo=row.prazo,
            ordem=next_ordem,
        )
        next_ordem += 1
        session.add(novo)
        session.flush()
        resolved_passos.append((novo.id, row.alcancado, row.observacao))

    # Progresso = media simples das % das actividades (ou payload se nao houver)
    if payload.actividades:
        progresso = sum(a.pct_conclusao for a in payload.actividades) / len(payload.actividades)
    else:
        progresso = float(payload.progresso or 0)

    data_sub = payload.data_sub or date.today()

    avaliacao = Avaliacao(
        pilar_id=pilar.id,
        user_id=user.id,
        estado_geral=payload.estado_geral or "",
        desafios=payload.desafios or "",
        licoes=payload.licoes or "",
        orc_obs=payload.orc_obs,
        recomendacoes=payload.recomendacoes,
        comentarios=payload.comentarios,
        progresso=float(progresso),
        assinatura=payload.assinatura,
        data_sub=data_sub,
    )
    session.add(avaliacao)
    session.flush()

    for row in payload.actividades:
        pct = int(row.pct_conclusao)
        estado = _estado_from_pct(pct)
        session.add(
            AvaliacaoActividade(
                avaliacao_id=avaliacao.id,
                pilar_actividade_id=row.pilar_actividade_id,
                estado=estado,
                pct_conclusao=pct,
                data_inicio_real=row.data_inicio_real,
                data_fim_real=row.data_fim_real,
                obs_execucao=row.obs_execucao,
            )
        )

    for row in payload.orcamentos:
        session.add(
            AvaliacaoOrcamento(
                avaliacao_id=avaliacao.id,
                categoria_id=row.categoria_id,
                valor_executado=row.valor_executado,
                forma_execucao=row.forma_execucao,
                obs=row.obs,
            )
        )

    for row in payload.riscos:
        session.add(
            AvaliacaoRisco(
                avaliacao_id=avaliacao.id,
                risco_id=row.risco_id,
                observacao=row.observacao,
            )
        )

    for passo_id, alcancado, observacao in resolved_passos:
        session.add(
            AvaliacaoProximoPasso(
                avaliacao_id=avaliacao.id,
                passo_id=passo_id,
                alcancado=alcancado,
                observacao=observacao,
            )
        )

    _update_schedule(pilar, data_sub)
    session.flush()

    return AvaliacaoCreated(
        id=avaliacao.id,
        pilar_id=pilar.id,
        data_sub=data_sub,
        progresso=float(avaliacao.progresso),
    )


def _update_schedule(pilar: Pilar, data_sub: date) -> None:
    days = pilar.periodicidade_dias or 90
    open_days = pilar.dias_aberto or 7
    next_date = data_sub + timedelta(days=days)
    pilar.proxima_avaliacao = next_date
    pilar.prazo_limite = next_date + timedelta(days=open_days)
