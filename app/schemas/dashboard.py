"""Dashboard response schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.pilar import PilarDetail


class DashResumo(BaseModel):
    progresso: float = 0.0
    orcamento_pct: float = 0.0
    actividades_total: int = 0
    actividades_concluidas: int = 0
    actividades_em_progresso: int = 0
    actividades_pendentes: int = 0
    riscos_altos: int = 0


class DashActividade(BaseModel):
    nome: str
    responsavel: str
    estado: str
    pct_conclusao: int
    prioridade: str


class DashOrcamento(BaseModel):
    categoria: str
    valor_alocado: Decimal
    valor_executado: Decimal


class DashRisco(BaseModel):
    descricao: str
    probabilidade: str
    impacto: str
    mitigacao: str | None = None
    observacao: str | None = None


class DashPasso(BaseModel):
    descricao: str
    responsavel: str
    prazo: date | None = None
    alcancado: bool = False


class DashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pilar: PilarDetail
    tem_avaliacao: bool
    avaliacao_id: int | None = None
    data_sub: date | None = None
    estado_geral: str | None = None
    desafios: str | None = None
    licoes: str | None = None
    recomendacoes: str | None = None
    comentarios: str | None = None
    progresso: float = 0.0
    resumo: DashResumo
    objectivos: list[str] = []
    actividades: list[DashActividade] = []
    orcamentos: list[DashOrcamento] = []
    riscos: list[DashRisco] = []
    proximos_passos: list[DashPasso] = []
