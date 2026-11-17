"""Serviço do monitor: contexto da carteira, fundamentos, preço e ranking."""
from __future__ import annotations

import math
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from typing import Any

from api.config import portfolio_path
from src.analytics.risk import PricePoint, calculate_risk
from src.importer import load_snapshot
from src.monitor.backtest import BacktestReport, evaluate
from src.monitor.config import MonitorConfig, load_config
from src.monitor.scoring import (
    CLASS_BUCKETS,
    Candidate,
    PortfolioContext,
    aggregate_signals,
    fundamentals_from_observations,
    rank_candidates,
)
from src.persistence.monitor import CandidateSnapshot
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


def _available_series(repositories: Any) -> dict[str, Any]:
    return {
        series.instrument_id: series
        for series in repositories.observations.series_keys(metric="close")
        if series.instrument_id
    }


def _momentum(repositories: Any, keys: list[str]) -> dict[str, dict[str, float]]:
    available = _available_series(repositories)

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


def _price_series(repositories: Any, keys: list[str]) -> dict[str, tuple[str, str]]:
    available = _available_series(repositories)
    result: dict[str, tuple[str, str]] = {}
    for key in keys:
        if not key.startswith("ticker:"):
            continue
        ticker = key.split(":", 1)[1]
        series = available.get(ticker) or available.get(f"{ticker}.SAO")
        if series is not None and series.instrument_id:
            result[key] = (series.provider, series.instrument_id)
    return result


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

    series_map = _price_series(repositories, [item.key for item in ranked])
    enriched = []
    for item in ranked:
        info = series_map.get(item.key)
        if info is not None:
            enriched.append(
                replace(
                    item,
                    price_provider=info[0],
                    price_instrument=info[1],
                )
            )
        else:
            enriched.append(item)
    ranked = enriched

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


def reference_prices(
    repositories: Any, keys: list[str], as_of: date
) -> dict[str, dict[str, object]]:
    available = {
        series.instrument_id: series
        for series in repositories.observations.series_keys(metric="close")
        if series.instrument_id
    }
    result: dict[str, dict[str, object]] = {}
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
        usable = [item for item in observations if item.reference_date <= as_of]
        if not usable:
            continue
        last = usable[-1]
        result[key] = {
            "price": float(last.value),
            "date": last.reference_date,
            "provider": series.provider,
            "instrument": series.instrument_id,
        }
    return result


def record_candidates_snapshot(
    repositories: Any,
    candidates: list[Candidate],
    *,
    snapshot_date: date,
    now: datetime,
) -> int:
    prices = reference_prices(repositories, [item.key for item in candidates], snapshot_date)
    snapshots: list[CandidateSnapshot] = []
    for candidate in candidates:
        price = prices.get(candidate.key)
        snapshots.append(
            CandidateSnapshot(
                snapshot_date=snapshot_date,
                asset_key=candidate.key,
                name=candidate.name,
                asset_class=candidate.asset_class,
                score=candidate.score,
                confidence=candidate.confidence,
                components=candidate.components,
                reasons=candidate.reasons,
                sources=candidate.sources,
                signal_count=candidate.signal_count,
                reference_price=float(price["price"]) if price else None,  # type: ignore[arg-type]
                reference_price_date=price["date"] if price else None,  # type: ignore[arg-type]
                price_provider=str(price["provider"]) if price else None,
                price_instrument=str(price["instrument"]) if price else None,
                created_at=now,
            )
        )
    return repositories.snapshots.record_many(snapshots, now=now)


def backtest(
    repositories: Any,
    *,
    horizon_days: int = 30,
    min_samples: int = 5,
    since_days: int = 365,
    now: datetime | None = None,
) -> BacktestReport:
    reference = now or datetime.now(timezone.utc)
    since = reference.date() - timedelta(days=since_days)
    snapshots = repositories.snapshots.list(since=since, limit=5000)
    pairs = {
        (snapshot.price_provider, snapshot.price_instrument)
        for snapshot in snapshots
        if snapshot.price_provider and snapshot.price_instrument
    }
    prices: dict[tuple[str, str], list[tuple[date, float]]] = {}
    for provider, instrument in pairs:
        observations = repositories.observations.list(
            provider=provider, instrument_id=instrument, metric="close"
        )
        prices[(provider, instrument)] = [
            (item.reference_date, float(item.value)) for item in observations
        ]
    return evaluate(
        snapshots, prices, horizon_days=horizon_days, min_samples=min_samples
    )
