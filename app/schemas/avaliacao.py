"""Avaliacao create/read schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ActividadeEstado


class AvaliacaoActividadeIn(BaseModel):
    pilar_actividade_id: int
    estado: ActividadeEstado = ActividadeEstado.pendente
    pct_conclusao: int = Field(default=0, ge=0, le=100)
    data_inicio_real: date | None = None
    data_fim_real: date | None = None
    obs_execucao: str | None = None


class AvaliacaoOrcamentoIn(BaseModel):
    categoria_id: int
    valor_executado: Decimal = Decimal("0")
    forma_execucao: str | None = None
    obs: str | None = None


class AvaliacaoRiscoIn(BaseModel):
    risco_id: int
    observacao: str | None = None


class AvaliacaoPassoIn(BaseModel):
    passo_id: int | None = None
    descricao: str | None = None
    responsavel: str | None = None
    prazo: date | None = None
    alcancado: bool = False
    observacao: str | None = None


class AvaliacaoCreate(BaseModel):
    pilar_id: int
    estado_geral: str = ""
    desafios: str = ""
    licoes: str = ""
    orc_obs: str | None = None
    recomendacoes: str | None = None
    comentarios: str | None = None
    progresso: float = Field(default=0, ge=0, le=100)
    assinatura: str | None = None
    data_sub: date | None = None
    actividades: list[AvaliacaoActividadeIn] = Field(default_factory=list)
    orcamentos: list[AvaliacaoOrcamentoIn] = Field(default_factory=list)
    riscos: list[AvaliacaoRiscoIn] = Field(default_factory=list)
    proximos_passos: list[AvaliacaoPassoIn] = Field(default_factory=list)


class AvaliacaoCreated(BaseModel):
    id: int
    pilar_id: int
    data_sub: date | None = None
    progresso: float
    message: str = "Avaliacao submetida com sucesso."


class AvaliacaoListItem(BaseModel):
    id: int
    pilar_id: int
    pilar_nome: str
    data_sub: date | None = None
    progresso: float
    estado_geral: str = ""
    autor: str | None = None


class AvaliacaoDetailOut(BaseModel):
    id: int
    pilar_id: int
    pilar_nome: str
    data_sub: date | None = None
    progresso: float
    autor: str | None = None
    actividades: list[dict] = Field(default_factory=list)
    orcamentos: list[dict] = Field(default_factory=list)
    riscos: list[dict] = Field(default_factory=list)
    proximos_passos: list[dict] = Field(default_factory=list)
    anexos: list[dict] = Field(default_factory=list)
