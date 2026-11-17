"""Serviço do monitor: contexto da carteira, fundamentos, preço e ranking."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from api.config import portfolio_path
from src.analytics.risk import PricePoint, calculate_risk
from src.importer import load_snapshot
from src.monitor.config import MonitorConfig, load_config
from src.monitor.scoring import (
    CLASS_BUCKETS,
    Candidate,
    PortfolioContext,
    aggregate_signals,
    fundamentals_from_observations,
    rank_candidates,
)
from src.portfolio import positions_frame


def _portfolio_context(config: MonitorConfig) -> PortfolioContext:
    path = portfolio_path()
    if not path.exists():
        raise FileNotFoundError("Importe uma carteira primeiro.")
    snapshot = load_snapshot(path)
    frame = positions_frame(snapshot)

    total = 0.0
    values_by_class: dict[str, float] = {}
    holdings: dict[str, float] = {}
    for _, row in frame.iterrows():
        value = row["Valor consolidado BRL"]
        if value is None:
            continue
        value_brl = float(value)
        if not math.isfinite(value_brl) or value_brl <= 0:
            continue
        total += value_brl
        bucket = CLASS_BUCKETS.get(str(row["Classe"]), "outros")
        values_by_class[bucket] = values_by_class.get(bucket, 0.0) + value_brl
        ticker = row["Ticker"]
        if isinstance(ticker, str) and ticker:
            holdings[ticker] = holdings.get(ticker, 0.0) + value_brl

    if total <= 0:
        raise ValueError("Sem posições com valor consolidado em BRL.")

    return PortfolioContext(
        total_brl=total,
        allocation={key: value / total for key, value in values_by_class.items()},
        holdings={key: value / total for key, value in holdings.items()},
        targets=config.targets,
        max_asset_share=config.max_asset_share,
    )


def _fundamentals(repositories: Any) -> dict[str, dict[str, float | None]]:
    observations = repositories.observations.latest_by_series(
        provider="cvm", metrics=("revenue", "net_income", "equity")
    )
    return fundamentals_from_observations(observations)


def _momentum(repositories: Any, keys: list[str]) -> dict[str, dict[str, float]]:
    available = {}
    for series in repositories.observations.series_keys(metric="close"):
        if series.instrument_id:
            available[series.instrument_id] = series

    momentum: dict[str, dict[str, float]] = {}
    for key in keys:
        if not key.startswith("ticker:"):
            continue
        ticker = key.split(":", 1)[1]
        series = available.get(ticker) or available.get(f"{ticker}.SAO")
        if series is None:
            continue
        observations = repositories.observations.list(
            provider=series.provider, instrument_id=series.instrument_id, metric="close"
        )
        points = [
            PricePoint(day=item.reference_date, value=float(item.value))
            for item in observations
        ]
        if len(points) < 21:
            continue
        window = points[-64:]
        report = calculate_risk(window)
        if report.total_return is None:
            continue
        momentum[key] = {
            "return": report.total_return,
            "volatility": report.annualized_volatility or 0.0,
            "points": report.observations,
        }
    return momentum


def candidates(
    repositories: Any,
    *,
    config: MonitorConfig | None = None,
    now: datetime | None = None,
    limit: int = 50,
    min_score: float = 0.0,
    asset_class: str | None = None,
) -> list[Candidate]:
    monitor_config = config or load_config()
    reference = now or datetime.now(timezone.utc)
    since = reference - timedelta(days=monitor_config.lookback_days)

    context = _portfolio_context(monitor_config)
    signals = repositories.signals.list(since=since, limit=2000)
    aggregates = aggregate_signals(
        signals,
        source_weights={source.name: source.weight for source in monitor_config.sources},
        now=reference,
        lookback_days=monitor_config.lookback_days,
    )
    ranked = rank_candidates(
        aggregates,
        context,
        fundamentals=_fundamentals(repositories),
        momentum=_momentum(repositories, [item.key for item in aggregates]),
        now=reference,
    )

    if asset_class:
        ranked = [item for item in ranked if item.asset_class == asset_class]
    if min_score > 0:
        ranked = [item for item in ranked if item.score >= min_score]
    return ranked[:limit]


def signals(
    repositories: Any,
    *,
    limit: int = 100,
    source: str | None = None,
    lookback_days: int | None = None,
    with_assets: bool = True,
) -> list:
    since = None
    if lookback_days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    return repositories.signals.list(
        since=since, source=source, with_assets=with_assets, limit=limit
    )
