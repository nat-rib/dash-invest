"""Serviço do motor de risco: séries armazenadas e histórico da carteira."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.analytics.risk import PricePoint, RiskReport, calculate_risk
from src.domain.observations import Observation
from src.history import portfolio_history


def _points(observations: Iterable[Observation]) -> list[PricePoint]:
    return [
        PricePoint(day=item.reference_date, value=float(item.value))
        for item in observations
    ]


def instrument_report(
    repositories: Any,
    *,
    provider: str,
    instrument_id: str,
    metric: str = "close",
    risk_free_rate: float = 0.0,
    benchmark_provider: str | None = None,
    benchmark_instrument_id: str | None = None,
    benchmark_metric: str = "close",
) -> RiskReport:
    observations = repositories.observations.list(
        provider=provider, instrument_id=instrument_id, metric=metric
    )
    benchmark = None
    if benchmark_provider and benchmark_instrument_id:
        benchmark = _points(
            repositories.observations.list(
                provider=benchmark_provider,
                instrument_id=benchmark_instrument_id,
                metric=benchmark_metric,
            )
        )
    return calculate_risk(
        _points(observations),
        risk_free_rate=risk_free_rate,
        benchmark=benchmark,
    )


def portfolio_report(*, risk_free_rate: float = 0.0) -> RiskReport:
    frame = portfolio_history()
    points: list[PricePoint] = []
    for _, row in frame.iterrows():
        value = float(row["Patrimônio BRL"])
        if value > 0:
            points.append(PricePoint(day=row["Data"].date(), value=value))
    return calculate_risk(points, risk_free_rate=risk_free_rate)
