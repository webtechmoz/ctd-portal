"""Authentication service — JWT cookie auth (no password in claims)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.models.enums import UserStatus
from app.models.user import User
from app.repositories import tokens as token_repo
from app.repositories import users as user_repo
from config.settings import settings

ALGORITHM = "HS256"
COOKIE_NAME = "access_token"


class AuthError(Exception):
    def __init__(self, code: str, message: str, status: int = 401):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def generate_temp_password(length: int = 12) -> str:
    """Palavra-passe temporaria (sem caracteres ambiguos I/O/l/0/1)."""
    import secrets
    import string

    upper = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    lower = "abcdefghijkmnopqrstuvwxyz"
    digits = "23456789"
    special = "!@#$"
    alphabet = upper + lower + digits + special
    picks = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    picks += [secrets.choice(alphabet) for _ in range(max(0, length - len(picks)))]
    secrets.SystemRandom().shuffle(picks)
    return "".join(picks)


def _email_allowed(email: str) -> bool:
    return settings.email_domain_allowed(email)


def create_access_token(user: User) -> tuple[str, datetime]:
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_TTL_HOURS)
    payload = {
        "sub": str(user.id),
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "jti": str(uuid4()),
        "exp": expires,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, expires


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def login(session: Session, email: str, password: str) -> tuple[User, str, datetime]:
    email_norm = email.strip().lower()
    if not _email_allowed(email_norm):
        allowed = ", ".join(settings.allowed_email_domains) or "(nenhum)"
        raise AuthError(
            "INVALID_EMAIL_DOMAIN",
            f"Email fora dos dominios permitidos ({allowed}).",
            401,
        )

    user = user_repo.get_by_email(session, email_norm)
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("INVALID_CREDENTIALS", "Email ou password invalidos.", 401)

    status = user.status.value if hasattr(user.status, "value") else user.status
    if status != UserStatus.active.value:
        raise AuthError("USER_INACTIVE", "Conta inactiva.", 403)

    token, expires = create_access_token(user)
    return user, token, expires


def get_user_from_token(session: Session, token: str | None) -> User:
    if not token:
        raise AuthError("UNAUTHENTICATED", "Autenticacao necessaria.", 401)

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("TOKEN_EXPIRED", "Sessao expirada.", 401) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("INVALID_TOKEN", "Token invalido.", 401) from exc

    jti = payload.get("jti")
    if not jti or token_repo.is_blacklisted(session, jti):
        raise AuthError("TOKEN_REVOKED", "Sessao invalidada.", 401)

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthError("INVALID_TOKEN", "Token invalido.", 401) from exc

    user = user_repo.get_by_id(session, user_id)
    if not user:
        raise AuthError("USER_NOT_FOUND", "Utilizador nao encontrado.", 401)

    status = user.status.value if hasattr(user.status, "value") else user.status
    if status != UserStatus.active.value:
        raise AuthError("USER_INACTIVE", "Conta inactiva.", 403)

    return user


def logout(session: Session, token: str | None) -> None:
    if not token:
        return
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        return

    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return

    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    token_repo.add(session, jti, expires_at)


def _cookie_flags() -> str:
    """Shared Path/HttpOnly/SameSite/Secure — login and logout must match."""
    secure = " Secure;" if settings.is_production else ""
    return f"Path=/; HttpOnly;{secure} SameSite=Lax"


def set_auth_cookie(app, token: str) -> None:
    # Bypass pyweber set_cookie (malformed SameSite/Expires; cannot Max-Age=0).
    max_age = int(settings.JWT_TTL_HOURS * 3600)
    expires = (
        datetime.now(timezone.utc) + timedelta(hours=settings.JWT_TTL_HOURS)
    ).strftime("%a, %d %b %Y %H:%M:%S GMT")
    app.cookies[COOKIE_NAME] = (
        f"{COOKIE_NAME}={token}; {_cookie_flags()}; "
        f"Max-Age={max_age}; Expires={expires};"
    )


def clear_auth_cookie(app) -> None:
    """Expire access_token. Pyweber set_cookie ignores max_age<=0."""
    expired = (
        f"{COOKIE_NAME}=; {_cookie_flags()}; "
        "Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT;"
    )
    app.cookies[COOKIE_NAME] = expired
    # Also clear a Secure variant in case an older login set Secure on HTTP
    if not settings.is_production:
        app.cookies[f"{COOKIE_NAME}__insecure_clear"] = (
            f"{COOKIE_NAME}=; Path=/; HttpOnly; Secure; SameSite=Lax; "
            "Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT;"
        )


def read_access_token(app) -> str | None:
    if not app.request:
        return None
    return app.request.cookies.get(COOKIE_NAME) or None
