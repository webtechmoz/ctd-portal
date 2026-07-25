"""Pilar master data models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Date,
    Enum,
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
from app.models.enums import (
    ActividadeStatus,
    Impacto,
    PilarStatus,
    Prioridade,
    Probabilidade,
    TimestampMixin,
)


class Pilar(Base, TimestampMixin):
    __tablename__ = "pilares"
    __table_args__ = (
        Index("ix_pilares_status_nome", "status", "nome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False, default="")
    area: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    fase: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    obj_geral: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kpis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    beneficios: Mapped[str] = mapped_column(Text, nullable=False, default="")
    plano_obs: Mapped[str | None] = mapped_column(Text, nullable=True)
    parceiros: Mapped[str | None] = mapped_column(Text, nullable=True)
    orc_aprovado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    orc_moeda: Mapped[str] = mapped_column(String(10), nullable=False, default="MZN")
    orc_fonte: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    periodicidade_dias: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    dias_aberto: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    proxima_avaliacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    prazo_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[PilarStatus] = mapped_column(
        Enum(PilarStatus, name="pilar_status", native_enum=False, length=20),
        default=PilarStatus.activo,
        nullable=False,
    )

    responsaveis = relationship(
        "PilarResponsavel",
        back_populates="pilar",
        cascade="all, delete-orphan",
    )
    objectivos = relationship(
        "PilarObjectivo",
        back_populates="pilar",
        cascade="all, delete-orphan",
        order_by="PilarObjectivo.ordem",
    )
    actividades = relationship(
        "PilarActividade",
        back_populates="pilar",
        cascade="all, delete-orphan",
        order_by="PilarActividade.ordem",
    )
    orcamento_categorias = relationship(
        "PilarOrcamentoCategoria",
        back_populates="pilar",
        cascade="all, delete-orphan",
        order_by="PilarOrcamentoCategoria.ordem",
    )
    riscos = relationship(
        "PilarRisco",
        back_populates="pilar",
        cascade="all, delete-orphan",
        order_by="PilarRisco.ordem",
    )
    proximos_passos = relationship(
        "PilarProximoPasso",
        back_populates="pilar",
        cascade="all, delete-orphan",
        order_by="PilarProximoPasso.ordem",
    )
    avaliacoes = relationship("Avaliacao", back_populates="pilar")


class PilarResponsavel(Base):
    __tablename__ = "pilar_responsaveis"
    __table_args__ = (UniqueConstraint("pilar_id", "user_id", name="uq_pilar_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pilar_id: Mapped[int] = mapped_column(ForeignKey("pilares.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    pilar = relationship("Pilar", back_populates="responsaveis")
    user = relationship("User", back_populates="pilares_responsavel")


class PilarObjectivo(Base):
    __tablename__ = "pilar_objectivos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pilar_id: Mapped[int] = mapped_column(ForeignKey("pilares.id", ondelete="CASCADE"), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    pilar = relationship("Pilar", back_populates="objectivos")


class PilarActividade(Base):
    __tablename__ = "pilar_actividades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pilar_id: Mapped[int] = mapped_column(ForeignKey("pilares.id", ondelete="CASCADE"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    responsavel: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    prioridade: Mapped[Prioridade] = mapped_column(
        Enum(Prioridade, name="prioridade", native_enum=False, length=20),
        default=Prioridade.media,
        nullable=False,
    )
    data_inicio_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    obs_planeamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ActividadeStatus] = mapped_column(
        Enum(ActividadeStatus, name="actividade_status", native_enum=False, length=20),
        default=ActividadeStatus.activa,
        nullable=False,
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    pilar = relationship("Pilar", back_populates="actividades")


class PilarOrcamentoCategoria(Base):
    __tablename__ = "pilar_orcamento_categorias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pilar_id: Mapped[int] = mapped_column(ForeignKey("pilares.id", ondelete="CASCADE"), nullable=False, index=True)
    categoria: Mapped[str] = mapped_column(String(150), nullable=False)
    valor_alocado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    obs: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    pilar = relationship("Pilar", back_populates="orcamento_categorias")


class PilarRisco(Base):
    __tablename__ = "pilar_riscos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pilar_id: Mapped[int] = mapped_column(ForeignKey("pilares.id", ondelete="CASCADE"), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    probabilidade: Mapped[Probabilidade] = mapped_column(
        Enum(Probabilidade, name="probabilidade", native_enum=False, length=20),
        default=Probabilidade.media,
        nullable=False,
    )
    impacto: Mapped[Impacto] = mapped_column(
        Enum(Impacto, name="impacto", native_enum=False, length=20),
        default=Impacto.medio,
        nullable=False,
    )
    mitigacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    pilar = relationship("Pilar", back_populates="riscos")


class PilarProximoPasso(Base):
    __tablename__ = "pilar_proximos_passos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pilar_id: Mapped[int] = mapped_column(ForeignKey("pilares.id", ondelete="CASCADE"), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    responsavel: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    prazo: Mapped[date | None] = mapped_column(Date, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    pilar = relationship("Pilar", back_populates="proximos_passos")
