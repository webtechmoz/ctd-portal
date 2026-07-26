"""Pilar repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import PilarStatus
from app.models.pilar import Pilar


def list_activos(session: Session) -> list[Pilar]:
    return list(
        session.scalars(
            select(Pilar)
            .where(Pilar.status == PilarStatus.activo)
            .order_by(Pilar.nome)
        ).all()
    )


def list_all(session: Session) -> list[Pilar]:
    return list(session.scalars(select(Pilar).order_by(Pilar.nome)).all())


def get_by_id(session: Session, pilar_id: int) -> Pilar | None:
    return session.get(Pilar, pilar_id)


def get_with_master(session: Session, pilar_id: int) -> Pilar | None:
    from app.models.pilar import PilarResponsavel

    return session.scalar(
        select(Pilar)
        .where(Pilar.id == pilar_id)
        .options(
            selectinload(Pilar.objectivos),
            selectinload(Pilar.actividades),
            selectinload(Pilar.orcamento_categorias),
            selectinload(Pilar.riscos),
            selectinload(Pilar.proximos_passos),
            selectinload(Pilar.responsaveis).selectinload(PilarResponsavel.user),
        )
    )
