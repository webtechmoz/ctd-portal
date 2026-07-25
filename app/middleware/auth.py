"""Auth / RBAC helpers for API handlers."""

from __future__ import annotations

import pyweber as pw
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User
from app.services import auth_service


class AuthContext:
    def __init__(self, user: User):
        self.user = user

    @property
    def role(self) -> UserRole:
        role = self.user.role
        return role if isinstance(role, UserRole) else UserRole(role)

    def require_roles(self, *roles: UserRole) -> None:
        if self.role not in roles:
            raise auth_service.AuthError(
                "FORBIDDEN",
                "Nao tem permissao para esta operacao.",
                403,
            )


def resolve_user(app: pw.Pyweber, session: Session) -> User:
    token = auth_service.read_access_token(app)
    return auth_service.get_user_from_token(session, token)


def require_auth(app: pw.Pyweber, session: Session, *roles: UserRole) -> AuthContext:
    user = resolve_user(app, session)
    ctx = AuthContext(user)
    if roles:
        ctx.require_roles(*roles)
    return ctx


def handle_auth_error(app: pw.Pyweber, exc: Exception):
    from app.api.http import api_error

    if isinstance(exc, auth_service.AuthError):
        return api_error(app, exc.status, exc.code, exc.message)
    raise exc
