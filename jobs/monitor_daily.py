"""CLI: snapshot diário do ranking + envio de alertas.

Uso:
    python -m jobs.monitor_daily
    python -m jobs.monitor_daily --min-score 85 --cooldown-days 5
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from api.services import monitor_service
from src.monitor.alerts import build_notifiers, send_alerts, settings_from_env
from src.persistence.database import SQLiteDatabase
from src.persistence.issuers import IssuerRepository
from src.persistence.monitor import AlertRepository, SnapshotRepository
from src.persistence.observations import ObservationRepository
from src.persistence.signals import SignalRepository
from src.persistence.watchlist import WatchlistRepository
from src.providers.alpha_vantage import AlphaVantageProvider


class Bundle:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.observations = ObservationRepository(database)
        self.signals = SignalRepository(database)
        self.issuers = IssuerRepository(database)
        self.snapshots = SnapshotRepository(database)
        self.alerts = AlertRepository(database)
        self.watchlist = WatchlistRepository(database)


def price_symbol(key: str, asset_class: str) -> str | None:
    if not key.startswith("ticker:"):
        return None
    ticker = key.split(":", 1)[1]
    if asset_class in {"acao", "fii", "etf"}:
        return f"{ticker}.SAO"
    if asset_class == "exterior":
        return ticker
    return None


def ingest_candidate_prices(
    bundle: Bundle, candidates: list, watchlist_items: list, *, max_symbols: int
) -> int:
    """Atualiza cotações da watchlist e dos candidatos do topo para o backtest."""
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if not api_key:
        print("aviso: ALPHA_VANTAGE_API_KEY ausente; preços de candidatos não atualizados")
        return 0

    provider = AlphaVantageProvider(api_key=api_key)
    entries = [(item.asset_key, item.asset_class) for item in watchlist_items]
    entries.extend((candidate.key, candidate.asset_class) for candidate in candidates)

    inserted = 0
    seen: set[str] = set()
    for key, asset_class in entries:
        if len(seen) >= max_symbols:
            break
        symbol = price_symbol(key, asset_class)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        currency = "BRL" if symbol.endswith(".SAO") else "USD"
        try:
            inserted += bundle.observations.record_many(
                provider.daily_prices(symbol, currency=currency)
            )
        except Exception as error:  # noqa: BLE001 - um símbolo não impede os demais
            print(f"aviso: preço {symbol}: {error}")
    print(f"{inserted} novas cotações para {len(seen)} ativo(s) monitorado(s)")
    return inserted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Registra snapshot do ranking e envia alertas."
    )
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--cooldown-days", type=int, default=None)
    parser.add_argument("--max-alerts", type=int, default=None)
    parser.add_argument(
        "--max-price-symbols",
        type=int,
        default=10,
        help="quantos tickers de candidatos atualizar por execução",
    )
    parser.add_argument(
        "--skip-prices",
        action="store_true",
        help="não consulta cotações de candidatos",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="envia uma mensagem de teste pelos canais configurados e sai",
    )
    args = parser.parse_args(argv)

    database = SQLiteDatabase(
        args.db or os.environ.get("DASH_INVEST_DB_PATH", "data/dash_invest.db")
    )
    database.initialize()
    bundle = Bundle(database)
    now = datetime.now(timezone.utc)

    settings = settings_from_env()
    notifiers = build_notifiers(settings)
    if args.test:
        for notifier in notifiers:
            try:
                notifier.send("Teste de alerta do Dash-Invest ✅")
                print(f"teste enviado por {notifier.name}")
            except Exception as error:  # noqa: BLE001
                print(f"erro em {notifier.name}: {error}")
        return 0

    try:
        candidates = monitor_service.candidates(bundle, limit=200, now=now)
    except (FileNotFoundError, ValueError) as error:
        print(f"erro: {error}")
        return 1

    if not args.skip_prices:
        ingest_candidate_prices(
            bundle,
            candidates,
            bundle.watchlist.list(),
            max_symbols=args.max_price_symbols,
        )

    inserted = monitor_service.record_candidates_snapshot(
        bundle, candidates, snapshot_date=now.date(), now=now
    )

    min_score = args.min_score if args.min_score is not None else settings.min_score
    cooldown_days = (
        args.cooldown_days if args.cooldown_days is not None else settings.cooldown_days
    )
    max_alerts = (
        args.max_alerts if args.max_alerts is not None else settings.max_alerts
    )

    result = send_alerts(
        candidates,
        bundle.alerts,
        notifiers,
        min_score=min_score,
        cooldown_days=cooldown_days,
        now=now,
        max_alerts=max_alerts,
    )

    print(
        f"{inserted} snapshots atualizados · {len(result.sent)} alertas enviados · "
        f"{result.skipped_cooldown} em cooldown · "
        f"{result.skipped_below_score} abaixo de {min_score:.0f}"
    )
    for key, score, channels in result.sent:
        print(f"alerta: {key} score {score:.0f} -> {', '.join(channels)}")
    for error in result.errors:
        print(f"erro: {error}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
