"""Anexo repository."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.anexo import Anexo
from app.models.pilar import Pilar
from app.models.user import User


def list_for_source(session: Session, source_type: str, source_id: int) -> list[Anexo]:
    return list(
        session.scalars(
            select(Anexo)
            .where(Anexo.source_type == source_type, Anexo.source_id == source_id)
            .options(selectinload(Anexo.uploaded_by), selectinload(Anexo.pilar))
            .order_by(Anexo.id.desc())
        ).all()
    )


def get_by_id(session: Session, anexo_id: int) -> Anexo | None:
    return session.scalar(
        select(Anexo)
        .where(Anexo.id == anexo_id)
        .options(selectinload(Anexo.uploaded_by), selectinload(Anexo.pilar))
    )


def search_paginated(
    session: Session,
    *,
    q: str = "",
    page: int = 1,
    page_size: int = 20,
    source_type: str | None = None,
) -> tuple[list[Anexo], int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    stmt = select(Anexo).options(selectinload(Anexo.uploaded_by), selectinload(Anexo.pilar))
    count_stmt = select(func.count()).select_from(Anexo)

    if source_type:
        stmt = stmt.where(Anexo.source_type == source_type)
        count_stmt = count_stmt.where(Anexo.source_type == source_type)

    q = (q or "").strip()
    if q:
        like = f"%{q}%"
        filt = or_(
            Anexo.original_name.ilike(like),
            Anexo.source_label.ilike(like),
            Anexo.source_type.ilike(like),
            Anexo.content_type.ilike(like),
            Pilar.nome.ilike(like),
            User.name.ilike(like),
        )
        stmt = stmt.outerjoin(Pilar, Anexo.pilar_id == Pilar.id).outerjoin(
            User, Anexo.uploaded_by_id == User.id
        ).where(filt)
        count_stmt = (
            count_stmt.outerjoin(Pilar, Anexo.pilar_id == Pilar.id)
            .outerjoin(User, Anexo.uploaded_by_id == User.id)
            .where(filt)
        )

    total = int(session.scalar(count_stmt) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(Anexo.id.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
    )
    return rows, total
