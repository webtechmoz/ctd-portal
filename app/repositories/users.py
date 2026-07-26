"""User repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import UserRole, UserStatus
from app.models.user import User


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.lower().strip()))


def get_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def list_users(
    session: Session,
    *,
    role: UserRole | None = None,
    status: UserStatus | None = None,
) -> list[User]:
    stmt = select(User).order_by(User.name.asc())
    if role is not None:
        stmt = stmt.where(User.role == role)
    if status is not None:
        stmt = stmt.where(User.status == status)
    return list(session.scalars(stmt).all())


def create_user(
    session: Session,
    *,
    name: str,
    email: str,
    password_hash: str,
    role: UserRole,
    must_change_password: bool = True,
) -> User:
    user = User(
        name=name.strip(),
        email=email.lower().strip(),
        password_hash=password_hash,
        role=role,
        status=UserStatus.active,
        must_change_password=must_change_password,
    )
    session.add(user)
    session.flush()
    return user
