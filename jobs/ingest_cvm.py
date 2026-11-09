"""CLI: ingere fundamentos da CVM (DFP) no banco de observações.

Uso:
    python -m jobs.ingest_cvm --year 2024
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingere fundamentos da CVM DFP.")
    parser.add_argument("--year", type=int, required=True, help="exercício fiscal da DFP")
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

    provider = CvmDfpProvider(consolidated=not args.individual)
    result = FundamentalsIngestion(
        provider=provider,
        repository=ObservationRepository(database),
        issuers=IssuerRepository(database),
    ).run(args.year)

    print(
        f"{result.observations} novas observações e "
        f"{result.issuers} novos emissores da CVM DFP {args.year}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
