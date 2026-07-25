"""Anexo schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AnexoOut(BaseModel):
    id: int
    original_name: str
    content_type: str
    size_bytes: int
    source_type: str
    source_id: int
    source_label: str
    pilar_id: int | None = None
    pilar_nome: str | None = None
    uploaded_by: str | None = None
    created_at: datetime | None = None
    download_url: str = ""


class AnexoListResponse(BaseModel):
    anexos: list[AnexoOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    pages: int = 1
    page_size: int = 20
