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
    PilarRisco,
)
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
}


def _calc_proxima(periodicidade_dias: int) -> date:
    return date.today() + timedelta(days=max(1, periodicidade_dias or 90))


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


def _append_nested(pilar: Pilar, data: PilarUpdate) -> None:
    base_obj = len(pilar.objectivos)
    for i, row in enumerate(data.objectivos or []):
        pilar.objectivos.append(
            PilarObjectivo(descricao=row.descricao, ordem=base_obj + i)
        )
    base_act = len(pilar.actividades)
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
                ordem=base_act + i,
            )
        )
    base_orc = len(pilar.orcamento_categorias)
    for i, row in enumerate(data.orcamento_categorias or []):
        pilar.orcamento_categorias.append(
            PilarOrcamentoCategoria(
                categoria=row.categoria,
                valor_alocado=row.valor_alocado,
                obs=row.obs,
                ordem=base_orc + i,
            )
        )
    base_risco = len(pilar.riscos)
    for i, row in enumerate(data.riscos or []):
        pilar.riscos.append(
            PilarRisco(
                descricao=row.descricao,
                probabilidade=row.probabilidade,
                impacto=row.impacto,
                mitigacao=row.mitigacao,
                ordem=base_risco + i,
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
        }
    )
    payload["nome"] = data.nome.strip()
    if not payload.get("proxima_avaliacao"):
        payload["proxima_avaliacao"] = _calc_proxima(payload.get("periodicidade_dias") or 90)
    pilar = Pilar(**payload)
    session.add(pilar)
    session.flush()
    _set_nested_create(pilar, data)
    session.flush()
    refreshed = pilar_repo.get_with_master(session, pilar.id)
    return PilarMasterOut.model_validate(refreshed)


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
    session.flush()
    refreshed = pilar_repo.get_with_master(session, pilar.id)
    return PilarMasterOut.model_validate(refreshed)


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
