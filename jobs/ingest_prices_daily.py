"""CLI: atualiza diariamente as cotações das posições da carteira.

Uso (no container):
    python -m jobs.ingest_prices_daily
    python -m jobs.ingest_prices_daily --max-symbols 10
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.application.portfolio_prices import DEFAULT_MAX_SYMBOLS, ingest_portfolio_prices
from src.importer import load_snapshot
from src.persistence.database import SQLiteDatabase
from src.persistence.observations import ObservationRepository
from src.providers.alpha_vantage import AlphaVantageProvider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atualiza cotações diárias da carteira.")
    parser.add_argument(
        "--portfolio",
        type=Path,
        default=None,
        help="snapshot JSON (padrão: PORTFOLIO_PATH)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="caminho do SQLite (padrão: DASH_INVEST_DB_PATH)",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=DEFAULT_MAX_SYMBOLS,
        help="limite de símbolos por execução (cota do provedor)",
    )
    args = parser.parse_args(argv)

    portfolio_path = args.portfolio or Path(
        os.environ.get("PORTFOLIO_PATH", "portfolio.json")
    )
    if not portfolio_path.exists():
        parser.error(f"carteira não encontrada: {portfolio_path}")

    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if not api_key:
        parser.error("defina ALPHA_VANTAGE_API_KEY")

    database = SQLiteDatabase(
        args.db or os.environ.get("DASH_INVEST_DB_PATH", "data/dash_invest.db")
    )
    database.initialize()

    snapshot = load_snapshot(portfolio_path)
    summary = ingest_portfolio_prices(
        snapshot,
        AlphaVantageProvider(api_key=api_key),
        ObservationRepository(database),
        max_symbols=args.max_symbols,
    )

    print(
        f"{summary.inserted} novas cotações em {len(summary.fetched)} símbolos "
        f"({', '.join(summary.fetched) or 'nenhum'})"
    )
    if summary.skipped:
        print(f"Adiados por limite de {args.max_symbols}: {', '.join(summary.skipped)}")
    for error in summary.errors:
        print(f"erro: {error}")

    if not summary.fetched:
        return 1
    if summary.errors and len(summary.errors) == len(summary.fetched):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
