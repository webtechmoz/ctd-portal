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
from app.models.enums import (
    ActividadeEstado,
    ActividadeStatus,
    AvaliacaoStatus,
    PilarStatus,
    UserRole,
    utcnow,
)
from app.models.pilar import Pilar, PilarProximoPasso, PilarResponsavel
from app.models.user import User
from app.repositories import avaliacoes as aval_repo
from app.repositories import pilares as pilar_repo
from app.schemas.avaliacao import AvaliacaoCreate, AvaliacaoCreated
from app.services import auth_service
from app.services.rbac_service import user_has_permission


def user_can_evaluate(session: Session, user: User, pilar_id: int) -> bool:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role == UserRole.admin.value:
        return True
    if not user_has_permission(session, user, "avaliacao.submit"):
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

    st = pilar.status.value if hasattr(pilar.status, "value") else str(pilar.status)
    if st != PilarStatus.activo.value:
        raise auth_service.AuthError(
            "CONFLICT",
            "So e possivel submeter avaliacoes em projectos activos "
            f"(estado actual: {st}).",
            409,
        )

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

    act_by_id = {a.id: a for a in pilar.actividades}
    act_ids = set(act_by_id)
    cancelled_ids = {
        a.id
        for a in pilar.actividades
        if (a.status.value if hasattr(a.status, "value") else str(a.status))
        == ActividadeStatus.cancelada.value
    }
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
        if row.pilar_actividade_id in cancelled_ids:
            raise auth_service.AuthError(
                "VALIDATION_ERROR",
                f"Actividade «{act_by_id[row.pilar_actividade_id].nome}» esta cancelada e nao pode receber dados.",
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

    resolved_passos: list[tuple[int, bool, str | None, bool]] = []
    next_ordem = len(pilar.proximos_passos)
    for row in payload.proximos_passos:
        if row.passo_id is not None:
            if row.passo_id not in passo_ids:
                raise auth_service.AuthError(
                    "VALIDATION_ERROR",
                    f"Passo {row.passo_id} nao pertence ao pilar.",
                    422,
                )
            resolved_passos.append((row.passo_id, row.alcancado, row.observacao, False))
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
        resolved_passos.append((novo.id, row.alcancado, row.observacao, True))

    # Progresso = media das % das actividades activas (canceladas excluidas)
    active_rows = [
        a for a in payload.actividades if a.pilar_actividade_id not in cancelled_ids
    ]
    if active_rows:
        progresso = sum(a.pct_conclusao for a in active_rows) / len(active_rows)
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
        status=AvaliacaoStatus.submetida,
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

    for passo_id, alcancado, observacao, criado_nesta in resolved_passos:
        session.add(
            AvaliacaoProximoPasso(
                avaliacao_id=avaliacao.id,
                passo_id=passo_id,
                alcancado=alcancado,
                observacao=observacao,
                criado_nesta_avaliacao=criado_nesta,
            )
        )

    _update_schedule(pilar, data_sub)
    session.flush()

    try:
        from app.services.notification_service import notify_pending_validation

        notify_pending_validation(session, avaliacao)
    except Exception:
        pass

    return AvaliacaoCreated(
        id=avaliacao.id,
        pilar_id=pilar.id,
        data_sub=data_sub,
        progresso=float(avaliacao.progresso),
        status=AvaliacaoStatus.submetida,
    )


def _status_val(avaliacao: Avaliacao) -> str:
    return avaliacao.status.value if hasattr(avaliacao.status, "value") else str(avaliacao.status)


def _assert_editable(avaliacao: Avaliacao) -> None:
    st = _status_val(avaliacao)
    if st == AvaliacaoStatus.validada.value:
        raise auth_service.AuthError(
            "CONFLICT",
            "Avaliacao validada. Peca ao coordenador para reabrir se precisar editar.",
            409,
        )
    if st not in {AvaliacaoStatus.submetida.value, AvaliacaoStatus.reaberta.value}:
        raise auth_service.AuthError("CONFLICT", "Estado da avaliacao nao permite edicao.", 409)


def update_avaliacao(
    session: Session, user: User, avaliacao_id: int, payload: AvaliacaoCreate
) -> AvaliacaoCreated:
    avaliacao = aval_repo.get_by_id(session, avaliacao_id)
    if not avaliacao:
        raise auth_service.AuthError("NOT_FOUND", "Avaliacao nao encontrada.", 404)
    _assert_editable(avaliacao)
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if (
        role != UserRole.admin.value
        and avaliacao.user_id != user.id
        and not user_can_evaluate(session, user, avaliacao.pilar_id)
    ):
        raise auth_service.AuthError("FORBIDDEN", "Sem permissao para editar esta avaliacao.", 403)

    pilar = pilar_repo.get_with_master(session, avaliacao.pilar_id)
    if not pilar:
        raise auth_service.AuthError("NOT_FOUND", "Pilar nao encontrado.", 404)

    cancelled_ids = {
        a.id
        for a in pilar.actividades
        if (a.status.value if hasattr(a.status, "value") else str(a.status))
        == ActividadeStatus.cancelada.value
    }
    for row in payload.actividades:
        if row.pilar_actividade_id in cancelled_ids:
            raise auth_service.AuthError(
                "VALIDATION_ERROR",
                "Actividade cancelada nao pode receber dados.",
                422,
            )

    old_criado = {
        p.passo_id: bool(getattr(p, "criado_nesta_avaliacao", False))
        for p in list(avaliacao.proximos_passos)
    }
    old_criado_ids = {pid for pid, flag in old_criado.items() if flag}

    for coll in (
        list(avaliacao.actividades),
        list(avaliacao.orcamentos),
        list(avaliacao.riscos),
        list(avaliacao.proximos_passos),
    ):
        for row in coll:
            session.delete(row)
    session.flush()

    active_rows = [a for a in payload.actividades if a.pilar_actividade_id not in cancelled_ids]
    if active_rows:
        progresso = sum(a.pct_conclusao for a in active_rows) / len(active_rows)
    else:
        progresso = float(payload.progresso or 0)

    data_sub = payload.data_sub or avaliacao.data_sub or date.today()
    avaliacao.estado_geral = payload.estado_geral or ""
    avaliacao.desafios = payload.desafios or ""
    avaliacao.licoes = payload.licoes or ""
    avaliacao.orc_obs = payload.orc_obs
    avaliacao.recomendacoes = payload.recomendacoes
    avaliacao.comentarios = payload.comentarios
    avaliacao.progresso = float(progresso)
    avaliacao.assinatura = payload.assinatura
    avaliacao.data_sub = data_sub
    if _status_val(avaliacao) == AvaliacaoStatus.reaberta.value:
        avaliacao.status = AvaliacaoStatus.submetida

    for row in payload.actividades:
        pct = int(row.pct_conclusao)
        session.add(
            AvaliacaoActividade(
                avaliacao_id=avaliacao.id,
                pilar_actividade_id=row.pilar_actividade_id,
                estado=_estado_from_pct(pct),
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

    passo_ids = {p.id for p in pilar.proximos_passos}
    next_ordem = len(pilar.proximos_passos)
    kept_passo_ids: set[int] = set()
    for row in payload.proximos_passos:
        passo_id = row.passo_id
        criado_nesta = False
        if passo_id is None:
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
            passo_id = novo.id
            passo_ids.add(passo_id)
            criado_nesta = True
        elif passo_id not in passo_ids:
            raise auth_service.AuthError(
                "VALIDATION_ERROR",
                f"Passo {passo_id} nao pertence ao pilar.",
                422,
            )
        else:
            criado_nesta = bool(old_criado.get(passo_id, False))
            master = next((p for p in pilar.proximos_passos if p.id == passo_id), None)
            if master is not None:
                if row.descricao is not None and (row.descricao or "").strip():
                    master.descricao = (row.descricao or "").strip()
                if row.responsavel is not None:
                    master.responsavel = (row.responsavel or "").strip()
                if row.prazo is not None:
                    master.prazo = row.prazo
        kept_passo_ids.add(passo_id)
        session.add(
            AvaliacaoProximoPasso(
                avaliacao_id=avaliacao.id,
                passo_id=passo_id,
                alcancado=row.alcancado,
                observacao=row.observacao,
                criado_nesta_avaliacao=criado_nesta,
            )
        )

    # Remover do master os passos criados nesta avaliacao e omitidos no PATCH.
    for pid in old_criado_ids - kept_passo_ids:
        still_linked = session.scalar(
            select(AvaliacaoProximoPasso.id).where(AvaliacaoProximoPasso.passo_id == pid).limit(1)
        )
        if still_linked:
            continue
        master = session.get(PilarProximoPasso, pid)
        if master is not None:
            session.delete(master)

    session.flush()
    try:
        from app.services.notification_service import notify_pending_validation

        notify_pending_validation(session, avaliacao)
    except Exception:
        pass
    return AvaliacaoCreated(
        id=avaliacao.id,
        pilar_id=avaliacao.pilar_id,
        data_sub=data_sub,
        progresso=float(avaliacao.progresso),
        status=AvaliacaoStatus(_status_val(avaliacao)),
        message="Avaliacao actualizada.",
    )


def validate_avaliacao(
    session: Session, user: User, avaliacao_id: int, note: str | None = None
) -> Avaliacao:
    if not user_has_permission(session, user, "avaliacao.validate"):
        role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if role != UserRole.admin.value:
            raise auth_service.AuthError("FORBIDDEN", "Sem permissao para validar.", 403)
    avaliacao = aval_repo.get_by_id(session, avaliacao_id)
    if not avaliacao:
        raise auth_service.AuthError("NOT_FOUND", "Avaliacao nao encontrada.", 404)
    st = _status_val(avaliacao)
    if st == AvaliacaoStatus.validada.value:
        raise auth_service.AuthError("CONFLICT", "Avaliacao ja esta validada.", 409)
    avaliacao.status = AvaliacaoStatus.validada
    avaliacao.validated_by_id = user.id
    avaliacao.validated_at = utcnow()
    if note is not None:
        avaliacao.validation_note = note
    session.flush()
    try:
        from app.services.notification_service import clear_pending_validation_notifications

        clear_pending_validation_notifications(session, avaliacao.id)
    except Exception:
        pass
    return avaliacao


def reopen_avaliacao(
    session: Session, user: User, avaliacao_id: int, note: str | None = None
) -> Avaliacao:
    if not user_has_permission(session, user, "avaliacao.validate"):
        role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if role != UserRole.admin.value:
            raise auth_service.AuthError("FORBIDDEN", "Sem permissao para reabrir.", 403)
    avaliacao = aval_repo.get_by_id(session, avaliacao_id)
    if not avaliacao:
        raise auth_service.AuthError("NOT_FOUND", "Avaliacao nao encontrada.", 404)
    if _status_val(avaliacao) != AvaliacaoStatus.validada.value:
        raise auth_service.AuthError("CONFLICT", "So avaliacoes validadas podem ser reabertas.", 409)
    avaliacao.status = AvaliacaoStatus.reaberta
    avaliacao.reopened_by_id = user.id
    avaliacao.reopened_at = utcnow()
    if note is not None:
        avaliacao.validation_note = note
    session.flush()
    try:
        from app.services.notification_service import notify_pending_validation

        notify_pending_validation(session, avaliacao)
    except Exception:
        pass
    return avaliacao


def _update_schedule(pilar: Pilar, data_sub: date) -> None:
    st = pilar.status.value if hasattr(pilar.status, "value") else str(pilar.status)
    if st != "activo":
        return
    days = pilar.periodicidade_dias or 90
    open_days = pilar.dias_aberto or 7
    next_date = data_sub + timedelta(days=days)
    pilar.proxima_avaliacao = next_date
    pilar.prazo_limite = next_date + timedelta(days=open_days)
