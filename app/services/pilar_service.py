"""Pilar create / update service."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.avaliacao import Avaliacao, AvaliacaoActividade, AvaliacaoOrcamento, AvaliacaoRisco
from app.models.pilar import (
    Pilar,
    PilarActividade,
    PilarObjectivo,
    PilarOrcamentoCategoria,
    PilarProximoPasso,
    PilarResponsavel,
    PilarRisco,
)
from app.models.user import User
from app.repositories import pilares as pilar_repo
from app.schemas.pilar import PilarUpdate, PilarWrite
from app.schemas.pilar_master import PilarMasterOut
from app.services import auth_service

_NESTED = {
    "objectivos",
    "actividades",
    "orcamento_categorias",
    "riscos",
    "proximos_passos",
    "delete_actividade_ids",
    "delete_categoria_ids",
    "delete_risco_ids",
    "responsavel_user_id",
}


def _calc_proxima(periodicidade_dias: int) -> date:
    return date.today() + timedelta(days=max(1, periodicidade_dias or 90))


def _set_responsavel(session: Session, pilar: Pilar, user_id: int | None) -> None:
    pilar.responsaveis.clear()
    session.flush()
    if not user_id:
        return
    user = session.get(User, user_id)
    if not user:
        raise auth_service.AuthError("VALIDATION_ERROR", "Responsavel invalido.", 422)
    pilar.responsaveis.append(PilarResponsavel(user_id=user.id))


def _master_out(session: Session, pilar: Pilar) -> PilarMasterOut:
    data = PilarMasterOut.model_validate(pilar)
    link = pilar.responsaveis[0] if pilar.responsaveis else None
    if link:
        data.responsavel_user_id = link.user_id
        user = link.user or session.get(User, link.user_id)
        if user:
            data.responsavel_nome = user.name
            data.responsavel_email = user.email
    return data


def master_out(session: Session, pilar: Pilar) -> PilarMasterOut:
    return _master_out(session, pilar)


def _set_nested_create(pilar: Pilar, data: PilarWrite) -> None:
    for i, row in enumerate(data.objectivos or []):
        pilar.objectivos.append(
            PilarObjectivo(descricao=row.descricao, ordem=row.ordem if row.ordem else i)
        )
    for i, row in enumerate(data.actividades or []):
        pilar.actividades.append(
            PilarActividade(
                nome=row.nome,
                responsavel=row.responsavel or "",
                prioridade=row.prioridade,
                data_inicio_prevista=row.data_inicio_prevista,
                data_fim_prevista=row.data_fim_prevista,
                descricao=row.descricao,
                obs_planeamento=row.obs_planeamento,
                status=row.status,
                ordem=row.ordem if row.ordem else i,
            )
        )
    for i, row in enumerate(data.orcamento_categorias or []):
        pilar.orcamento_categorias.append(
            PilarOrcamentoCategoria(
                categoria=row.categoria,
                valor_alocado=row.valor_alocado,
                obs=row.obs,
                ordem=row.ordem if row.ordem else i,
            )
        )
    for i, row in enumerate(data.riscos or []):
        pilar.riscos.append(
            PilarRisco(
                descricao=row.descricao,
                probabilidade=row.probabilidade,
                impacto=row.impacto,
                mitigacao=row.mitigacao,
                ordem=row.ordem if row.ordem else i,
            )
        )
    for i, row in enumerate(data.proximos_passos or []):
        pilar.proximos_passos.append(
            PilarProximoPasso(
                descricao=row.descricao,
                responsavel=row.responsavel or "",
                prazo=row.prazo,
                ordem=row.ordem if row.ordem else i,
            )
        )


def _sync_orc_aprovado(pilar: Pilar) -> None:
    """Orcamento global = soma das rubricas (fonte unica de verdade)."""
    total = sum(
        (Decimal(str(c.valor_alocado or 0)) for c in pilar.orcamento_categorias),
        Decimal("0"),
    )
    pilar.orc_aprovado = total


def _append_nested(pilar: Pilar, data: PilarUpdate) -> None:
    base_obj = len(pilar.objectivos)
    for i, row in enumerate(data.objectivos or []):
        pilar.objectivos.append(
            PilarObjectivo(descricao=row.descricao, ordem=base_obj + i)
        )
    base_act = len(pilar.actividades)
    for i, row in enumerate(data.actividades or []):
        if row.id:
            act = next((a for a in pilar.actividades if a.id == row.id), None)
            if act:
                act.nome = row.nome
                act.responsavel = row.responsavel or ""
                act.prioridade = row.prioridade
                act.data_inicio_prevista = row.data_inicio_prevista
                act.data_fim_prevista = row.data_fim_prevista
                act.descricao = row.descricao
                act.obs_planeamento = row.obs_planeamento
                act.status = row.status
                if row.ordem:
                    act.ordem = row.ordem
                continue
        pilar.actividades.append(
            PilarActividade(
                nome=row.nome,
                responsavel=row.responsavel or "",
                prioridade=row.prioridade,
                data_inicio_prevista=row.data_inicio_prevista,
                data_fim_prevista=row.data_fim_prevista,
                descricao=row.descricao,
                obs_planeamento=row.obs_planeamento,
                status=row.status,
                ordem=row.ordem if row.ordem else base_act + i,
            )
        )
    base_orc = len(pilar.orcamento_categorias)
    for i, row in enumerate(data.orcamento_categorias or []):
        if row.id:
            cat = next((c for c in pilar.orcamento_categorias if c.id == row.id), None)
            if cat:
                cat.categoria = row.categoria
                cat.valor_alocado = row.valor_alocado
                cat.obs = row.obs
                if row.ordem:
                    cat.ordem = row.ordem
                continue
        pilar.orcamento_categorias.append(
            PilarOrcamentoCategoria(
                categoria=row.categoria,
                valor_alocado=row.valor_alocado,
                obs=row.obs,
                ordem=row.ordem if row.ordem else base_orc + i,
            )
        )
    base_risco = len(pilar.riscos)
    for i, row in enumerate(data.riscos or []):
        if row.id:
            risco = next((r for r in pilar.riscos if r.id == row.id), None)
            if risco:
                risco.descricao = row.descricao
                risco.probabilidade = row.probabilidade
                risco.impacto = row.impacto
                risco.mitigacao = row.mitigacao
                if row.ordem:
                    risco.ordem = row.ordem
                continue
        pilar.riscos.append(
            PilarRisco(
                descricao=row.descricao,
                probabilidade=row.probabilidade,
                impacto=row.impacto,
                mitigacao=row.mitigacao,
                ordem=row.ordem if row.ordem else base_risco + i,
            )
        )
    base_passo = len(pilar.proximos_passos)
    for i, row in enumerate(data.proximos_passos or []):
        pilar.proximos_passos.append(
            PilarProximoPasso(
                descricao=row.descricao,
                responsavel=row.responsavel or "",
                prazo=row.prazo,
                ordem=base_passo + i,
            )
        )


def _categoria_has_execution(session: Session, categoria_id: int) -> bool:
    total = session.scalar(
        select(func.coalesce(func.sum(AvaliacaoOrcamento.valor_executado), 0)).where(
            AvaliacaoOrcamento.categoria_id == categoria_id
        )
    )
    return Decimal(str(total or 0)) > 0


def _apply_deletes(session: Session, pilar: Pilar, data: PilarUpdate) -> None:
    for aid in data.delete_actividade_ids or []:
        act = next((a for a in pilar.actividades if a.id == aid), None)
        if not act:
            continue
        used = session.scalar(
            select(func.count())
            .select_from(AvaliacaoActividade)
            .where(AvaliacaoActividade.pilar_actividade_id == aid)
        )
        if used:
            raise auth_service.AuthError(
                "CONFLICT",
                f"Nao e possivel remover a actividade «{act.nome}»: ja usada em avaliacoes.",
                409,
            )
        session.delete(act)

    for cid in data.delete_categoria_ids or []:
        cat = next((c for c in pilar.orcamento_categorias if c.id == cid), None)
        if not cat:
            continue
        if _categoria_has_execution(session, cid):
            raise auth_service.AuthError(
                "CONFLICT",
                f"Nao e possivel remover a rubrica «{cat.categoria}»: ja tem execucao orcamental.",
                409,
            )
        used = session.scalar(
            select(func.count())
            .select_from(AvaliacaoOrcamento)
            .where(AvaliacaoOrcamento.categoria_id == cid)
        )
        if used:
            raise auth_service.AuthError(
                "CONFLICT",
                f"Nao e possivel remover a rubrica «{cat.categoria}»: referida em avaliacoes.",
                409,
            )
        session.delete(cat)

    for rid in data.delete_risco_ids or []:
        risco = next((r for r in pilar.riscos if r.id == rid), None)
        if not risco:
            continue
        used = session.scalar(
            select(func.count())
            .select_from(AvaliacaoRisco)
            .where(AvaliacaoRisco.risco_id == rid)
        )
        if used:
            raise auth_service.AuthError(
                "CONFLICT",
                f"Nao e possivel remover o risco: ja referido em avaliacoes.",
                409,
            )
        session.delete(risco)


def create_pilar(session: Session, data: PilarWrite) -> PilarMasterOut:
    exists = session.scalar(select(Pilar).where(Pilar.nome == data.nome.strip()))
    if exists:
        raise auth_service.AuthError("CONFLICT", "Ja existe um projecto com este nome.", 409)

    payload = data.model_dump(
        exclude={
            "objectivos",
            "actividades",
            "orcamento_categorias",
            "riscos",
            "proximos_passos",
            "responsavel_user_id",
        }
    )
    payload["nome"] = data.nome.strip()
    if not payload.get("proxima_avaliacao"):
        payload["proxima_avaliacao"] = _calc_proxima(payload.get("periodicidade_dias") or 90)
    pilar = Pilar(**payload)
    session.add(pilar)
    session.flush()
    _set_nested_create(pilar, data)
    _set_responsavel(session, pilar, data.responsavel_user_id)
    session.flush()
    _sync_orc_aprovado(pilar)
    session.flush()
    refreshed = pilar_repo.get_with_master(session, pilar.id)
    return _master_out(session, refreshed)


def update_pilar(session: Session, pilar_id: int, data: PilarUpdate) -> PilarMasterOut:
    pilar = pilar_repo.get_with_master(session, pilar_id)
    if not pilar:
        raise auth_service.AuthError("NOT_FOUND", "Projecto nao encontrado.", 404)

    fields = data.model_dump(exclude_unset=True, exclude=_NESTED)
    if "nome" in fields and fields["nome"]:
        fields["nome"] = fields["nome"].strip()
        clash = session.scalar(
            select(Pilar).where(Pilar.nome == fields["nome"], Pilar.id != pilar_id)
        )
        if clash:
            raise auth_service.AuthError("CONFLICT", "Ja existe um projecto com este nome.", 409)

    period_changed = "periodicidade_dias" in fields
    for key, value in fields.items():
        setattr(pilar, key, value)

    if period_changed and "proxima_avaliacao" not in fields:
        pilar.proxima_avaliacao = _calc_proxima(pilar.periodicidade_dias)

    _apply_deletes(session, pilar, data)
    session.flush()
    _append_nested(pilar, data)
    if "responsavel_user_id" in data.model_fields_set:
        _set_responsavel(session, pilar, data.responsavel_user_id)
    session.flush()
    _sync_orc_aprovado(pilar)
    session.flush()
    refreshed = pilar_repo.get_with_master(session, pilar.id)
    return _master_out(session, refreshed)


def delete_pilar(session: Session, pilar_id: int) -> None:
    pilar = pilar_repo.get_by_id(session, pilar_id)
    if not pilar:
        raise auth_service.AuthError("NOT_FOUND", "Projecto nao encontrado.", 404)

    eval_count = session.scalar(
        select(func.count()).select_from(Avaliacao).where(Avaliacao.pilar_id == pilar_id)
    )
    if eval_count:
        raise auth_service.AuthError(
            "CONFLICT",
            "Nao e possivel apagar: projecto tem avaliacoes. Desactive em vez de apagar.",
            409,
        )

    session.delete(pilar)
    session.flush()
