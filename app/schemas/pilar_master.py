"""Nested pilar master schemas for form preload."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActividadeStatus, Impacto, PilarStatus, Prioridade, Probabilidade
from app.schemas.pilar import PilarDetail


class ObjectivoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    descricao: str
    ordem: int


class ActividadeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    responsavel: str
    prioridade: Prioridade
    data_inicio_prevista: date | None = None
    data_fim_prevista: date | None = None
    descricao: str | None = None
    obs_planeamento: str | None = None
    status: ActividadeStatus = ActividadeStatus.activa
    ordem: int


class OrcamentoCatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    categoria: str
    valor_alocado: Decimal
    obs: str | None = None
    ordem: int


class RiscoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    descricao: str
    probabilidade: Probabilidade
    impacto: Impacto
    mitigacao: str | None = None
    ordem: int


class PassoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    descricao: str
    responsavel: str
    prazo: date | None = None
    ordem: int


class ResponsavelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    name: str | None = None
    email: str | None = None


class PilarMasterOut(PilarDetail):
    objectivos: list[ObjectivoOut] = Field(default_factory=list)
    actividades: list[ActividadeOut] = Field(default_factory=list)
    orcamento_categorias: list[OrcamentoCatOut] = Field(default_factory=list)
    riscos: list[RiscoOut] = Field(default_factory=list)
    proximos_passos: list[PassoOut] = Field(default_factory=list)
    responsavel_user_id: int | None = None
    responsavel_nome: str | None = None
    responsavel_email: str | None = None
