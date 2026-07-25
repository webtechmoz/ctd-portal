"""Pilar schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActividadeStatus, Impacto, PilarStatus, Prioridade, Probabilidade


class PilarListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    area: str
    fase: str
    status: PilarStatus
    proxima_avaliacao: date | None = None
    progresso_recente: float | None = None


class PilarDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    descricao: str
    area: str
    fase: str
    obj_geral: str
    kpis: str
    beneficios: str
    plano_obs: str | None = None
    parceiros: str | None = None
    orc_aprovado: Decimal | None = None
    orc_moeda: str
    orc_fonte: str | None = None
    data_inicio: date | None = None
    data_fim_prevista: date | None = None
    periodicidade_dias: int
    dias_aberto: int
    proxima_avaliacao: date | None = None
    prazo_limite: date | None = None
    status: PilarStatus


class ObjectivoIn(BaseModel):
    descricao: str
    ordem: int = 0


class ActividadeIn(BaseModel):
    id: int | None = None  # se presente em PATCH, actualiza a actividade existente
    nome: str
    responsavel: str = ""
    prioridade: Prioridade = Prioridade.media
    data_inicio_prevista: date | None = None
    data_fim_prevista: date | None = None
    descricao: str | None = None
    obs_planeamento: str | None = None
    status: ActividadeStatus = ActividadeStatus.activa
    ordem: int = 0


class OrcamentoCatIn(BaseModel):
    id: int | None = None  # se presente em PATCH, actualiza a rubrica existente
    categoria: str
    valor_alocado: Decimal = Decimal("0")
    obs: str | None = None
    ordem: int = 0


class RiscoIn(BaseModel):
    id: int | None = None  # se presente em PATCH, actualiza o risco existente
    descricao: str
    probabilidade: Probabilidade = Probabilidade.media
    impacto: Impacto = Impacto.medio
    mitigacao: str | None = None
    ordem: int = 0


class PassoIn(BaseModel):
    descricao: str
    responsavel: str = ""
    prazo: date | None = None
    ordem: int = 0


class PilarWrite(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    descricao: str = ""
    area: str = ""
    fase: str = ""
    obj_geral: str = ""
    kpis: str = ""
    beneficios: str = ""
    plano_obs: str | None = None
    parceiros: str | None = None
    orc_aprovado: Decimal | None = None
    orc_moeda: str = "MZN"
    orc_fonte: str | None = None
    data_inicio: date | None = None
    data_fim_prevista: date | None = None
    periodicidade_dias: int = Field(default=90, ge=1, le=3650)
    dias_aberto: int = Field(default=7, ge=0, le=365)
    proxima_avaliacao: date | None = None
    prazo_limite: date | None = None
    status: PilarStatus = PilarStatus.activo
    objectivos: list[ObjectivoIn] | None = None
    actividades: list[ActividadeIn] | None = None
    orcamento_categorias: list[OrcamentoCatIn] | None = None
    riscos: list[RiscoIn] | None = None
    proximos_passos: list[PassoIn] | None = None


class PilarUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=150)
    descricao: str | None = None
    area: str | None = None
    fase: str | None = None
    obj_geral: str | None = None
    kpis: str | None = None
    beneficios: str | None = None
    plano_obs: str | None = None
    parceiros: str | None = None
    orc_aprovado: Decimal | None = None
    orc_moeda: str | None = None
    orc_fonte: str | None = None
    data_inicio: date | None = None
    data_fim_prevista: date | None = None
    periodicidade_dias: int | None = Field(default=None, ge=1, le=3650)
    dias_aberto: int | None = Field(default=None, ge=0, le=365)
    proxima_avaliacao: date | None = None
    prazo_limite: date | None = None
    status: PilarStatus | None = None
    objectivos: list[ObjectivoIn] | None = None
    actividades: list[ActividadeIn] | None = None
    orcamento_categorias: list[OrcamentoCatIn] | None = None
    riscos: list[RiscoIn] | None = None
    proximos_passos: list[PassoIn] | None = None
    delete_actividade_ids: list[int] = Field(default_factory=list)
    delete_categoria_ids: list[int] = Field(default_factory=list)
    delete_risco_ids: list[int] = Field(default_factory=list)
