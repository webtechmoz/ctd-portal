"""Page helpers — load HTML shells from frontend/."""

from __future__ import annotations

from pathlib import Path

import pyweber as pw

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def html_page(relative_path: str) -> pw.Template:
    path = (FRONTEND_DIR / relative_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Pagina nao encontrada: {path}")
    return pw.Template(template=str(path))
