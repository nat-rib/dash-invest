"""CLI: coleta sinais de notícias via RSS."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.monitor.collector import collect
from src.monitor.config import load_config
from src.persistence.database import SQLiteDatabase
from src.persistence.issuers import IssuerRepository
from src.persistence.signals import SignalRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Coleta sinais de fontes RSS.")
    parser.add_argument("--config", type=Path, default=None, help="JSON de fontes e alvos")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--sleep", type=float, default=0.3, help="pausa entre fontes (s)")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="reextrai ativos de sinais já existentes (mesmo link)",
    )
    args = parser.parse_args(argv)

    database = SQLiteDatabase(
        args.db or os.environ.get("DASH_INVEST_DB_PATH", "data/dash_invest.db")
    )
    database.initialize()

    config = load_config(args.config)
    issuers = {issuer.cnpj: issuer.name for issuer in IssuerRepository(database).list()}
    summary = collect(
        config,
        SignalRepository(database),
        issuers=issuers,
        sleep=args.sleep,
        refresh=args.refresh,
    )

    print(
        f"{summary.inserted} sinais {'atualizados' if args.refresh else 'novos'} "
        f"de {summary.sources_ok} fonte(s) ({summary.items} itens lidos)"
    )
    if summary.sources_failed:
        print(f"{summary.sources_failed} fonte(s) falharam")
    for error in summary.errors:
        print(f"erro: {error}")
    return 0 if summary.sources_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
