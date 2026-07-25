"""File storage — local disk (default) or Cloudflare R2 when configured."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from config.settings import settings

MAX_UPLOAD_BYTES = 12 * 1024 * 1024  # 12 MB
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".txt",
    ".csv",
    ".zip",
}


def upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR)
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def r2_enabled() -> bool:
    return bool(
        settings.R2_ENDPOINT_URL.strip()
        and settings.R2_ACCESS_KEY_ID.strip()
        and settings.R2_SECRET_ACCESS_KEY.strip()
        and settings.R2_BUCKET.strip()
    )


def sanitize_filename(name: str) -> str:
    base = Path(name or "ficheiro").name
    base = re.sub(r"[^\w.\- ()\[\]]+", "_", base, flags=re.UNICODE).strip(" ._")
    return (base or "ficheiro")[:200]


def validate_upload(filename: str, size: int) -> str:
    if size <= 0:
        raise ValueError("Ficheiro vazio.")
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(f"Ficheiro excede o limite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Tipo de ficheiro nao permitido ({ext or 'sem extensao'}).")
    return ext


def build_storage_key(source_type: str, source_id: int, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    safe = sanitize_filename(filename)
    stem = Path(safe).stem[:80]
    token = uuid.uuid4().hex[:12]
    return f"{source_type}/{source_id}/{token}_{stem}{ext}"


def save_bytes(storage_key: str, data: bytes) -> None:
    if r2_enabled():
        _r2_put(storage_key, data)
        return
    path = upload_root() / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def read_bytes(storage_key: str) -> bytes:
    if r2_enabled():
        return _r2_get(storage_key)
    path = upload_root() / storage_key
    if not path.is_file():
        raise FileNotFoundError(storage_key)
    return path.read_bytes()


def delete_bytes(storage_key: str) -> None:
    if r2_enabled():
        _r2_delete(storage_key)
        return
    path = upload_root() / storage_key
    if path.is_file():
        path.unlink()


def _r2_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def _r2_put(key: str, data: bytes) -> None:
    _r2_client().put_object(Bucket=settings.R2_BUCKET, Key=key, Body=data)


def _r2_get(key: str) -> bytes:
    obj = _r2_client().get_object(Bucket=settings.R2_BUCKET, Key=key)
    return obj["Body"].read()


def _r2_delete(key: str) -> None:
    _r2_client().delete_object(Bucket=settings.R2_BUCKET, Key=key)
