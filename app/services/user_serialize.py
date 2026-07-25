"""Serialize users for API responses."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import UserPublic
from app.services.rbac_service import get_user_permission_codes


def user_to_public(session: Session, user: User) -> dict:
    perms = sorted(get_user_permission_codes(session, user))
    perfil_nome = None
    if user.perfil:
        perfil_nome = user.perfil.name
    elif user.role_id:
        from app.models.rbac import Role

        role = session.get(Role, user.role_id)
        if role:
            perfil_nome = role.name

    data = UserPublic.model_validate(user).model_dump(mode="json")
    data["permissions"] = perms
    data["perfil_nome"] = perfil_nome
    data["role_id"] = user.role_id
    return data
