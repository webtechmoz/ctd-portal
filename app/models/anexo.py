"""Anexo (uploaded file) model — linked to a source entity (e.g. avaliacao)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TimestampMixin


class Anexo(Base, TimestampMixin):
    __tablename__ = "anexos"
    __table_args__ = (
        Index("ix_anexos_source", "source_type", "source_id"),
        Index("ix_anexos_pilar_id", "pilar_id"),
        Index("ix_anexos_original_name", "original_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Where it was uploaded from
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="avaliacao")
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    pilar_id: Mapped[int | None] = mapped_column(
        ForeignKey("pilares.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_by = relationship("User")
    pilar = relationship("Pilar")
