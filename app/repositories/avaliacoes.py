"""Avaliacao repository helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.avaliacao import Avaliacao
from app.models.pilar import Pilar


def get_latest_for_pilar(session: Session, pilar_id: int) -> Avaliacao | None:
    return session.scalar(
        select(Avaliacao)
        .where(Avaliacao.pilar_id == pilar_id)
        .options(
            selectinload(Avaliacao.actividades),
            selectinload(Avaliacao.orcamentos),
            selectinload(Avaliacao.riscos),
            selectinload(Avaliacao.proximos_passos),
        )
        .order_by(Avaliacao.data_sub.desc(), Avaliacao.id.desc())
        .limit(1)
    )


def list_avaliacoes(
    session: Session,
    *,
    pilar_id: int | None = None,
    limit: int = 100,
) -> list[Avaliacao]:
    stmt = (
        select(Avaliacao)
        .options(selectinload(Avaliacao.pilar), selectinload(Avaliacao.user))
        .order_by(Avaliacao.data_sub.desc(), Avaliacao.id.desc())
        .limit(min(max(limit, 1), 500))
    )
    if pilar_id is not None:
        stmt = stmt.where(Avaliacao.pilar_id == pilar_id)
    return list(session.scalars(stmt).all())


def get_by_id(session: Session, avaliacao_id: int) -> Avaliacao | None:
    return session.scalar(
        select(Avaliacao)
        .where(Avaliacao.id == avaliacao_id)
        .options(
            selectinload(Avaliacao.pilar).options(
                selectinload(Pilar.actividades),
                selectinload(Pilar.orcamento_categorias),
                selectinload(Pilar.riscos),
                selectinload(Pilar.proximos_passos),
            ),
            selectinload(Avaliacao.user),
            selectinload(Avaliacao.actividades),
            selectinload(Avaliacao.orcamentos),
            selectinload(Avaliacao.riscos),
            selectinload(Avaliacao.proximos_passos),
        )
    )
