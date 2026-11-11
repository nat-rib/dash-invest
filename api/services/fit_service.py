"""Serviço do Portfolio Fit: snapshot + séries de preço para correlação."""
from __future__ import annotations

import math
from typing import Any

from api.config import portfolio_path
from src.analytics.portfolio_fit import (
    CorrelationPair,
    FitInput,
    PortfolioFit,
    build_fit,
)
from src.analytics.risk import PricePoint, correlation
from src.importer import load_snapshot
from src.portfolio import positions_frame


def _series_by_position(repositories: Any, inputs: list[FitInput]) -> dict[str, list[PricePoint]]:
    keys = repositories.observations.series_keys(metric="close")
    available = {}
    for key in keys:
        if not key.instrument_id:
            continue
        current = available.get(key.instrument_id)
        if current is None or key.observations > current.observations:
            available[key.instrument_id] = key

    series: dict[str, list[PricePoint]] = {}
    for item in inputs:
        if not item.ticker:
            continue
        for symbol in (item.ticker, f"{item.ticker}.SAO"):
            key = available.get(symbol)
            if key is None:
                continue
            observations = repositories.observations.list(
                provider=key.provider, instrument_id=symbol, metric="close"
            )
            if observations:
                series[item.name] = [
                    PricePoint(day=observation.reference_date, value=float(observation.value))
                    for observation in observations
                ]
            break
    return series


def _correlations(series: dict[str, list[PricePoint]]) -> list[CorrelationPair]:
    names = sorted(series)
    pairs: list[CorrelationPair] = []
    for left_index, left in enumerate(names):
        for right in names[left_index + 1:]:
            value = correlation(series[left], series[right])
            if value is not None:
                pairs.append(
                    CorrelationPair(
                        left=left,
                        right=right,
                        correlation=value,
                        observations=min(len(series[left]), len(series[right])),
                    )
                )
    return pairs


def build(repositories: Any) -> PortfolioFit:
    path = portfolio_path()
    if not path.exists():
        raise FileNotFoundError("Importe uma carteira primeiro.")
    snapshot = load_snapshot(path)
    frame = positions_frame(snapshot)

    inputs: list[FitInput] = []
    for _, row in frame.iterrows():
        value = row["Valor consolidado BRL"]
        if value is None:
            continue
        value_brl = float(value)
        if not math.isfinite(value_brl) or value_brl <= 0:
            continue
        ticker = row["Ticker"]
        inputs.append(
            FitInput(
                name=row["Nome"],
                institution=row["Instituição"],
                asset_class=row["Classe"],
                currency=row["Moeda"],
                value_brl=value_brl,
                liquidity=row["Liquidez"],
                risk_category=row["Categoria de risco"],
                ticker=ticker if isinstance(ticker, str) and ticker else None,
            )
        )

    return build_fit(inputs, correlations=_correlations(_series_by_position(repositories, inputs)))
