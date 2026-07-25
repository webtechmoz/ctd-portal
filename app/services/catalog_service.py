"""Catalog options service."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.catalog_seed import CATALOG_SEED
from app.models.catalog import CatalogOption
from app.models.pilar import Pilar
from app.services import auth_service


def ensure_catalog_seed(session: Session) -> None:
    for category, rows in CATALOG_SEED.items():
        for i, (code, label) in enumerate(rows):
            exists = session.scalar(
                select(CatalogOption).where(
                    CatalogOption.category == category,
                    CatalogOption.code == code,
                )
            )
            if exists:
                continue
            session.add(
                CatalogOption(
                    category=category,
                    code=code,
                    label=label,
                    sort_order=i,
                    is_system=True,
                    active=True,
                )
            )


def list_by_category(session: Session, category: str, *, active_only: bool = True) -> list[CatalogOption]:
    stmt = select(CatalogOption).where(CatalogOption.category == category)
    if active_only:
        stmt = stmt.where(CatalogOption.active.is_(True))
    stmt = stmt.order_by(CatalogOption.sort_order, CatalogOption.label)
    return list(session.scalars(stmt).all())


def list_all(session: Session) -> list[CatalogOption]:
    return list(
        session.scalars(
            select(CatalogOption).order_by(
                CatalogOption.category, CatalogOption.sort_order, CatalogOption.label
            )
        ).all()
    )


def option_in_use(session: Session, opt: CatalogOption) -> bool:
    """True if value is referenced by a pilar field."""
    field_map = {
        "moeda": Pilar.orc_moeda,
        "fase": Pilar.fase,
        "fonte_financiamento": Pilar.orc_fonte,
        "area": Pilar.area,
    }
    col = field_map.get(opt.category)
    if col is None:
        return False
    # Match code or label (legacy free-text may store either)
    count = session.scalar(
        select(func.count())
        .select_from(Pilar)
        .where(or_(col == opt.code, col == opt.label))
    )
    return bool(count)


def create_option(session: Session, *, category: str, code: str, label: str) -> CatalogOption:
    code = code.strip()
    label = label.strip()
    if not code or not label:
        raise auth_service.AuthError("VALIDATION_ERROR", "Codigo e etiqueta obrigatorios.", 422)
    exists = session.scalar(
        select(CatalogOption).where(
            CatalogOption.category == category,
            CatalogOption.code == code,
        )
    )
    if exists:
        raise auth_service.AuthError("CONFLICT", "Ja existe esta opcao na lista.", 409)
    max_ord = session.scalar(
        select(func.max(CatalogOption.sort_order)).where(CatalogOption.category == category)
    )
    opt = CatalogOption(
        category=category,
        code=code,
        label=label,
        sort_order=(max_ord or 0) + 1,
        is_system=False,
        active=True,
    )
    session.add(opt)
    session.flush()
    return opt


def update_option(session: Session, opt_id: int, *, label: str | None = None, active: bool | None = None) -> CatalogOption:
    opt = session.get(CatalogOption, opt_id)
    if not opt:
        raise auth_service.AuthError("NOT_FOUND", "Opcao nao encontrada.", 404)
    if label is not None:
        opt.label = label.strip()
    if active is not None:
        opt.active = active
    session.flush()
    return opt


def delete_option(session: Session, opt_id: int) -> None:
    opt = session.get(CatalogOption, opt_id)
    if not opt:
        raise auth_service.AuthError("NOT_FOUND", "Opcao nao encontrada.", 404)
    if option_in_use(session, opt):
        raise auth_service.AuthError(
            "CONFLICT",
            "Nao e possivel remover: opcao associada a projectos. Desactive em vez de apagar.",
            409,
        )
    session.delete(opt)
    session.flush()
