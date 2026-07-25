"""Anexo service — create from uploaded files, serialize."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy.orm import Session

from app.models.anexo import Anexo
from app.models.avaliacao import Avaliacao
from app.models.user import User
from app.repositories import anexos as anexo_repo
from app.services import auth_service, storage
from app.schemas.anexo import AnexoOut


SOURCE_LABELS = {
    "avaliacao": "Avaliacao",
}


def _source_ref_url(source_type: str, source_id: int) -> str:
    if source_type == "avaliacao":
        return f"/avaliacoes?ver={source_id}"
    return "#"


def serialize_anexo(row: Anexo) -> dict:
    return AnexoOut(
        id=row.id,
        original_name=row.original_name,
        content_type=row.content_type or "application/octet-stream",
        size_bytes=row.size_bytes or 0,
        source_type=row.source_type,
        source_id=row.source_id,
        source_label=row.source_label or "",
        pilar_id=row.pilar_id,
        pilar_nome=row.pilar.nome if row.pilar else None,
        uploaded_by=row.uploaded_by.name if row.uploaded_by else None,
        created_at=row.created_at,
        download_url=f"/api/v1/anexos/{row.id}/download",
    ).model_dump(mode="json") | {
        "source_type_label": SOURCE_LABELS.get(row.source_type, row.source_type),
        "source_url": _source_ref_url(row.source_type, row.source_id),
    }


def list_anexos(
    session: Session,
    *,
    q: str = "",
    page: int = 1,
    page_size: int = 20,
    source_type: str | None = None,
) -> dict:
    rows, total = anexo_repo.search_paginated(
        session, q=q, page=page, page_size=page_size, source_type=source_type
    )
    pages = max(1, math.ceil(total / page_size) if page_size else 1)
    return {
        "anexos": [serialize_anexo(r) for r in rows],
        "total": total,
        "page": page,
        "pages": pages,
        "page_size": page_size,
    }


def create_for_avaliacao(
    session: Session,
    user: User,
    avaliacao: Avaliacao,
    files: list[Any],
) -> list[dict]:
    if not files:
        return []

    pilar_nome = avaliacao.pilar.nome if avaliacao.pilar else f"Pilar #{avaliacao.pilar_id}"
    data_sub = str(avaliacao.data_sub) if avaliacao.data_sub else "sem data"
    label = f"Avaliacao · {pilar_nome} · {data_sub}"

    created: list[Anexo] = []
    for f in files:
        filename = getattr(f, "filename", None) or "ficheiro"
        content = getattr(f, "content", None) or b""
        if isinstance(content, str):
            content = content.encode("utf-8")
        size = len(content) if content else int(getattr(f, "size", 0) or 0)
        ctype = getattr(f, "content_type", None) or "application/octet-stream"

        try:
            storage.validate_upload(filename, size)
        except ValueError as exc:
            raise auth_service.AuthError("VALIDATION_ERROR", str(exc), 422) from exc

        key = storage.build_storage_key("avaliacao", avaliacao.id, filename)
        try:
            storage.save_bytes(key, content)
        except Exception as exc:
            raise auth_service.AuthError(
                "UPLOAD_FAILED",
                f"Falha ao guardar ficheiro: {exc}",
                500,
            ) from exc

        row = Anexo(
            storage_key=key,
            original_name=storage.sanitize_filename(filename),
            content_type=str(ctype)[:120],
            size_bytes=size,
            uploaded_by_id=user.id,
            source_type="avaliacao",
            source_id=avaliacao.id,
            source_label=label,
            pilar_id=avaliacao.pilar_id,
        )
        session.add(row)
        created.append(row)

    session.flush()
    for row in created:
        session.refresh(row)
    return [serialize_anexo(r) for r in created]
