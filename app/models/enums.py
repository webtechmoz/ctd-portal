"""Shared SQLAlchemy mixins and enums."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class UserRole(str, enum.Enum):
    admin = "admin"
    member = "member"
    visitor = "visitor"


class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class PilarStatus(str, enum.Enum):
    activo = "activo"
    inactivo = "inactivo"


class Prioridade(str, enum.Enum):
    alta = "alta"
    media = "media"
    baixa = "baixa"


class Probabilidade(str, enum.Enum):
    alta = "alta"
    media = "media"
    baixa = "baixa"


class Impacto(str, enum.Enum):
    alto = "alto"
    medio = "medio"
    baixo = "baixo"


class ActividadeEstado(str, enum.Enum):
    pendente = "pendente"
    em_progresso = "em_progresso"
    concluida = "concluida"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
