"""Catalog defaults and helpers."""

from __future__ import annotations

# category -> list of (code, label)
CATALOG_SEED: dict[str, list[tuple[str, str]]] = {
    "moeda": [
        ("MZN", "MZN — Metical"),
        ("USD", "USD — Dolar"),
        ("EUR", "EUR — Euro"),
        ("ZAR", "ZAR — Rand"),
    ],
    "fase": [
        ("planeamento", "Planeamento"),
        ("arranque", "Arranque"),
        ("implementacao", "Implementacao"),
        ("monitoria", "Monitoria"),
        ("encerramento", "Encerramento"),
    ],
    "fonte_financiamento": [
        ("orcamento_estado", "Orcamento do Estado"),
        ("parceiro", "Parceiro / Doador"),
        ("misto", "Misto"),
        ("proprio", "Fundos proprios"),
    ],
    "area": [
        ("saude", "Saude"),
        ("tic", "TIC / Sistemas"),
        ("financeiro", "Financeiro"),
        ("infraestrutura", "Infraestrutura"),
        ("formacao", "Formacao"),
    ],
}

CATALOG_LABELS: dict[str, str] = {
    "moeda": "Moedas",
    "fase": "Fases do projecto",
    "fonte_financiamento": "Fontes de financiamento",
    "area": "Areas",
}
