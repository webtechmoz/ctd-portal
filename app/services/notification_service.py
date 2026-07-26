"""Notification service — create, sync due evaluations, mark read."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import UserRole, PilarStatus
from app.models.notification import Notification
from app.models.pilar import Pilar
from app.models.rbac import Permission, RolePermission
from app.models.user import User
from app.services.email_service import send_simple_notice
from app.services.rbac_service import user_has_permission
from config.settings import settings


def _login_base() -> str:
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    return (origins[0] if origins else f"http://localhost:{settings.bind_port}").rstrip("/")


def notify(
    session: Session,
    *,
    user_id: int,
    tipo: str,
    titulo: str,
    corpo: str = "",
    link: str | None = None,
    ref_type: str | None = None,
    ref_id: int | None = None,
    dedupe_key: str | None = None,
    email: bool = False,
) -> Notification | None:
    if dedupe_key:
        exists = session.scalar(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.tipo == tipo,
                Notification.ref_type == ref_type,
                Notification.ref_id == ref_id,
                Notification.dedupe_key == dedupe_key,
            )
        )
        if exists:
            return exists

    row = Notification(
        user_id=user_id,
        tipo=tipo,
        titulo=titulo,
        corpo=corpo,
        link=link,
        ref_type=ref_type,
        ref_id=ref_id,
        dedupe_key=dedupe_key,
    )
    session.add(row)
    session.flush()

    if email:
        user = session.get(User, user_id)
        if user and user.email:
            full = f"{_login_base()}{link}" if link and link.startswith("/") else link
            send_simple_notice(to=user.email, subject=titulo, body=corpo or titulo, link=full)
    return row


def _validator_user_ids(session: Session) -> set[int]:
    ids: set[int] = set()
    admins = session.scalars(select(User).where(User.role == UserRole.admin)).all()
    ids.update(u.id for u in admins)
    perm = session.scalar(select(Permission).where(Permission.code == "avaliacao.validate"))
    if perm:
        role_ids = session.scalars(
            select(RolePermission.role_id).where(RolePermission.permission_id == perm.id)
        ).all()
        if role_ids:
            users = session.scalars(select(User).where(User.role_id.in_(list(role_ids)))).all()
            ids.update(u.id for u in users)
    return ids


def sync_due_avaliacoes(session: Session, user: User) -> int:
    """Cria notificacoes de avaliacao devida/atrasada (dedupe por dia)."""
    today = date.today()
    key = today.isoformat()
    created = 0
    pilares = session.scalars(
        select(Pilar)
        .where(
            Pilar.proxima_avaliacao.is_not(None),
            Pilar.status == PilarStatus.activo,
        )
        .options(selectinload(Pilar.responsaveis))
    ).all()
    for p in pilares:
        days = (p.proxima_avaliacao - today).days
        if days > 7:
            continue
        if days < 0:
            tipo = "avaliacao_atraso"
            titulo = f"Avaliacao em atraso: {p.nome}"
            corpo = f"A proxima avaliacao de «{p.nome}» estava prevista para {p.proxima_avaliacao}."
        elif days == 0:
            tipo = "avaliacao_hoje"
            titulo = f"Avaliacao hoje: {p.nome}"
            corpo = f"Chegou o dia de avaliar «{p.nome}»."
        else:
            tipo = "avaliacao_breve"
            titulo = f"Avaliacao em {days} dia(s): {p.nome}"
            corpo = f"A proxima avaliacao de «{p.nome}» e em {p.proxima_avaliacao}."

        recipients = set()
        for link in p.responsaveis:
            recipients.add(link.user_id)
        if user_has_permission(session, user, "avaliacao.validate") or (
            user.role.value if hasattr(user.role, "value") else str(user.role)
        ) == UserRole.admin.value:
            recipients.add(user.id)
        for uid in recipients:
            if uid != user.id and uid not in {user.id}:
                # only sync for current user inbox to avoid mass-create on every poll
                pass
        # Only ensure notifications for the requesting user
        is_resp = any(l.user_id == user.id for l in p.responsaveis)
        is_val = user_has_permission(session, user, "avaliacao.validate") or (
            (user.role.value if hasattr(user.role, "value") else str(user.role)) == UserRole.admin.value
        )
        if not (is_resp or is_val):
            continue
        before = session.scalar(
            select(Notification.id).where(
                Notification.user_id == user.id,
                Notification.tipo == tipo,
                Notification.ref_type == "pilar",
                Notification.ref_id == p.id,
                Notification.dedupe_key == key,
            )
        )
        if before:
            continue
        notify(
            session,
            user_id=user.id,
            tipo=tipo,
            titulo=titulo,
            corpo=corpo,
            link=f"/avaliacao?pilar={p.id}",
            ref_type="pilar",
            ref_id=p.id,
            dedupe_key=key,
            email=(days <= 0),
        )
        created += 1
    return created


def notify_pending_validation(session: Session, avaliacao) -> None:
    for uid in _validator_user_ids(session):
        if uid == avaliacao.user_id:
            continue
        notify(
            session,
            user_id=uid,
            tipo="avaliacao_pendente_validacao",
            titulo="Avaliacao pendente de validacao",
            corpo=f"Nova avaliacao submetida (#{avaliacao.id}).",
            link=f"/avaliacoes?ver={avaliacao.id}",
            ref_type="avaliacao",
            ref_id=avaliacao.id,
            dedupe_key=str(avaliacao.id),
            email=True,
        )


def list_for_user(session: Session, user_id: int, *, limit: int = 40) -> list[Notification]:
    return list(
        session.scalars(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        ).all()
    )


def count_unread(session: Session, user_id: int) -> int:
    from sqlalchemy import func

    return int(
        session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.lida.is_(False))
        )
        or 0
    )


def mark_read(session: Session, user_id: int, notif_id: int) -> bool:
    row = session.get(Notification, notif_id)
    if not row or row.user_id != user_id:
        return False
    row.lida = True
    session.flush()
    return True


def mark_all_read(session: Session, user_id: int) -> int:
    rows = session.scalars(
        select(Notification).where(Notification.user_id == user_id, Notification.lida.is_(False))
    ).all()
    for r in rows:
        r.lida = True
    session.flush()
    return len(rows)
