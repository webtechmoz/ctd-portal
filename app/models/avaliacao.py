"""Avaliacao (execution snapshot) models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ActividadeEstado, TimestampMixin


class Avaliacao(Base, TimestampMixin):
    __tablename__ = "avaliacoes"
    __table_args__ = (
        # latest evaluation per pilar: ORDER BY data_sub DESC, id DESC
        Index("ix_avaliacoes_pilar_data_sub_id", "pilar_id", "data_sub", "id"),
        Index("ix_avaliacoes_user_data_sub", "user_id", "data_sub"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pilar_id: Mapped[int] = mapped_column(ForeignKey("pilares.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    estado_geral: Mapped[str] = mapped_column(Text, nullable=False, default="")
    desafios: Mapped[str] = mapped_column(Text, nullable=False, default="")
    licoes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    orc_obs: Mapped[str | None] = mapped_column(Text, nullable=True)
    recomendacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    comentarios: Mapped[str | None] = mapped_column(Text, nullable=True)
    progresso: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    assinatura: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_sub: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    pilar = relationship("Pilar", back_populates="avaliacoes")
    user = relationship("User", back_populates="avaliacoes")
    actividades = relationship(
        "AvaliacaoActividade",
        back_populates="avaliacao",
        cascade="all, delete-orphan",
    )
    orcamentos = relationship(
        "AvaliacaoOrcamento",
        back_populates="avaliacao",
        cascade="all, delete-orphan",
    )
    riscos = relationship(
        "AvaliacaoRisco",
        back_populates="avaliacao",
        cascade="all, delete-orphan",
    )
    proximos_passos = relationship(
        "AvaliacaoProximoPasso",
        back_populates="avaliacao",
        cascade="all, delete-orphan",
    )


class AvaliacaoActividade(Base):
    __tablename__ = "avaliacao_actividades"
    __table_args__ = (
        UniqueConstraint("avaliacao_id", "pilar_actividade_id", name="uq_av_actividade"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    avaliacao_id: Mapped[int] = mapped_column(
        ForeignKey("avaliacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pilar_actividade_id: Mapped[int] = mapped_column(
        ForeignKey("pilar_actividades.id", ondelete="RESTRICT"), nullable=False
    )
    estado: Mapped[ActividadeEstado] = mapped_column(
        Enum(ActividadeEstado, name="actividade_estado", native_enum=False, length=20),
        default=ActividadeEstado.pendente,
        nullable=False,
    )
    pct_conclusao: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_inicio_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    obs_execucao: Mapped[str | None] = mapped_column(Text, nullable=True)

    avaliacao = relationship("Avaliacao", back_populates="actividades")


class AvaliacaoOrcamento(Base):
    __tablename__ = "avaliacao_orcamentos"
    __table_args__ = (
        UniqueConstraint("avaliacao_id", "categoria_id", name="uq_av_orcamento"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    avaliacao_id: Mapped[int] = mapped_column(
        ForeignKey("avaliacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("pilar_orcamento_categorias.id", ondelete="RESTRICT"), nullable=False
    )
    valor_executado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    forma_execucao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    obs: Mapped[str | None] = mapped_column(Text, nullable=True)

    avaliacao = relationship("Avaliacao", back_populates="orcamentos")


class AvaliacaoRisco(Base):
    __tablename__ = "avaliacao_riscos"
    __table_args__ = (
        UniqueConstraint("avaliacao_id", "risco_id", name="uq_av_risco"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    avaliacao_id: Mapped[int] = mapped_column(
        ForeignKey("avaliacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    risco_id: Mapped[int] = mapped_column(
        ForeignKey("pilar_riscos.id", ondelete="RESTRICT"), nullable=False
    )
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    avaliacao = relationship("Avaliacao", back_populates="riscos")


class AvaliacaoProximoPasso(Base):
    __tablename__ = "avaliacao_proximos_passos"
    __table_args__ = (
        UniqueConstraint("avaliacao_id", "passo_id", name="uq_av_passo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    avaliacao_id: Mapped[int] = mapped_column(
        ForeignKey("avaliacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    passo_id: Mapped[int] = mapped_column(
        ForeignKey("pilar_proximos_passos.id", ondelete="RESTRICT"), nullable=False
    )
    alcancado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    avaliacao = relationship("Avaliacao", back_populates="proximos_passos")
