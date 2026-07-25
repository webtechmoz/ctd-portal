"""Seed CLI — admin/RBAC/catalog; opcionalmente projectos demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.bootstrap import bootstrap_database
from app.services.seed_service import run_seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed CTD Portal")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Tambem cria projectos demo (nao usar em producao)",
    )
    parser.add_argument(
        "--force-admin",
        action="store_true",
        default=True,
        help="Recria/actualiza password do admin a partir de SEED_* (default)",
    )
    args = parser.parse_args()

    bootstrap_database()
    run_seed(force_admin=args.force_admin, sample_data=args.sample or None)
    print("Seed concluido.")
    if args.sample:
        print("Incluiu projectos demo (--sample).")
    else:
        print("Sem projectos demo (use --sample localmente se precisar).")


if __name__ == "__main__":
    main()
