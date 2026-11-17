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


class Bundle:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.observations = ObservationRepository(database)
        self.signals = SignalRepository(database)
        self.issuers = IssuerRepository(database)
        self.snapshots = SnapshotRepository(database)
        self.alerts = AlertRepository(database)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Registra snapshot do ranking e envia alertas."
    )
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--cooldown-days", type=int, default=None)
    parser.add_argument("--max-alerts", type=int, default=None)
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
        f"{inserted} snapshots · {len(result.sent)} alertas enviados · "
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
