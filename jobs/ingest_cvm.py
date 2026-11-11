"""CLI: ingere fundamentos da CVM (DFP anual ou ITR trimestral).

Uso:
    python -m jobs.ingest_cvm --year 2024                  # DFP anual
    python -m jobs.ingest_cvm --year 2024 --dataset itr    # ITR trimestral
    python -m jobs.ingest_cvm --year 2024 --individual
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.application.fundamentals import FundamentalsIngestion
from src.persistence.database import SQLiteDatabase
from src.persistence.issuers import IssuerRepository
from src.persistence.observations import ObservationRepository
from src.providers.cvm import CvmDfpProvider
from src.providers.cvm_itr import CvmItrProvider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingere fundamentos da CVM.")
    parser.add_argument("--year", type=int, required=True, help="exercício fiscal")
    parser.add_argument(
        "--dataset",
        choices=("dfp", "itr"),
        default="dfp",
        help="dfp = anual; itr = trimestral",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="caminho do SQLite (padrão: DASH_INVEST_DB_PATH)",
    )
    parser.add_argument(
        "--individual",
        action="store_true",
        help="usa demonstrações individuais em vez de consolidadas",
    )
    args = parser.parse_args(argv)

    database = SQLiteDatabase(
        args.db or os.environ.get("DASH_INVEST_DB_PATH", "data/dash_invest.db")
    )
    database.initialize()

    consolidated = not args.individual
    provider = (
        CvmItrProvider(consolidated=consolidated)
        if args.dataset == "itr"
        else CvmDfpProvider(consolidated=consolidated)
    )
    result = FundamentalsIngestion(
        provider=provider,
        repository=ObservationRepository(database),
        issuers=IssuerRepository(database),
    ).run(args.year)

    print(
        f"{result.observations} novas observações e "
        f"{result.issuers} novos emissores da CVM {args.dataset.upper()} {args.year}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
