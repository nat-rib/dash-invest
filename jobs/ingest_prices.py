"""CLI: ingere uma série de preços diários no banco de observações.

Uso:
    python -m jobs.ingest_prices --symbol PETR4.SAO --csv precos.csv
    python -m jobs.ingest_prices --symbol PETR4.SAO --start 2024-01-01
"""
from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from src.application.prices import csv_price_observations, ingest_price_series
from src.persistence.database import SQLiteDatabase
from src.persistence.observations import ObservationRepository
from src.providers.alpha_vantage import AlphaVantageProvider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingere série diária de preços.")
    parser.add_argument("--symbol", required=True, help="símbolo do provedor (ex.: PETR4.SAO)")
    parser.add_argument("--currency", default="BRL", help="moeda da série (padrão: BRL)")
    parser.add_argument("--csv", type=Path, default=None, help="CSV com colunas de data e fechamento")
    parser.add_argument("--start", type=date.fromisoformat, default=None)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args(argv)

    database = SQLiteDatabase(
        args.db or os.environ.get("DASH_INVEST_DB_PATH", "data/dash_invest.db")
    )
    database.initialize()
    repository = ObservationRepository(database)

    if args.csv is not None:
        observations = csv_price_observations(
            args.csv.read_text(encoding="utf-8"),
            symbol=args.symbol,
            currency=args.currency,
            source_document=str(args.csv),
        )
        inserted = ingest_price_series(observations, repository)
        print(f"{inserted} novas cotações de {args.symbol} a partir de {args.csv}")
        return 0

    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
    if not api_key:
        parser.error("defina ALPHA_VANTAGE_API_KEY ou use --csv")

    provider = AlphaVantageProvider(api_key=api_key, currency=args.currency)
    inserted = ingest_price_series(
        provider.daily_prices(args.symbol, start=args.start, end=args.end),
        repository,
    )
    print(f"{inserted} novas cotações de {args.symbol} via {provider.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
