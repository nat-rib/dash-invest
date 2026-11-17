"""Avaliação do ranking: retorno futuro por faixa de score e correlação de postos."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from src.persistence.monitor import CandidateSnapshot

BUCKETS: tuple[tuple[float, float, str], ...] = (
    (0.0, 20.0, "0–20"),
    (20.0, 40.0, "20–40"),
    (40.0, 60.0, "40–60"),
    (60.0, 80.0, "60–80"),
    (80.0, 100.01, "80–100"),
)
MATURITY_TOLERANCE_DAYS = 7


@dataclass(frozen=True)
class ScoreBucket:
    label: str
    count: int
    average_return: float | None
    hit_rate: float | None


@dataclass(frozen=True)
class BacktestReport:
    snapshots: int
    evaluated: int
    horizon_days: int
    buckets: tuple[ScoreBucket, ...]
    rank_correlation: float | None
    top_average: float | None
    bottom_average: float | None
    spread: float | None
    available: bool
    reason: str | None


def _rank(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2 + 1
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1
    return ranks


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    numerator = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    denominator = math.sqrt(
        sum((a - mean_left) ** 2 for a in left)
        * sum((b - mean_right) ** 2 for b in right)
    )
    return numerator / denominator if denominator else None


def spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    return _pearson(_rank(left), _rank(right))


def evaluate(
    snapshots: Sequence[CandidateSnapshot],
    prices: Mapping[tuple[str, str], Sequence[tuple[date, float]]],
    *,
    horizon_days: int,
    min_samples: int = 5,
) -> BacktestReport:
    evaluated: list[tuple[float, float]] = []

    for snapshot in snapshots:
        if (
            snapshot.reference_price is None
            or not snapshot.price_provider
            or not snapshot.price_instrument
        ):
            continue
        series = prices.get((snapshot.price_provider, snapshot.price_instrument))
        if not series:
            continue
        target = snapshot.snapshot_date + timedelta(days=horizon_days)
        future = [
            (day, value)
            for day, value in series
            if snapshot.snapshot_date < day <= target
        ]
        if not future:
            continue
        last_day, last_price = future[-1]
        if last_day < target - timedelta(days=MATURITY_TOLERANCE_DAYS):
            continue
        if snapshot.reference_price <= 0:
            continue
        evaluated.append((snapshot.score, last_price / snapshot.reference_price - 1))

    buckets: list[ScoreBucket] = []
    for minimum, maximum, label in BUCKETS:
        returns = [value for score, value in evaluated if minimum <= score < maximum]
        if returns:
            buckets.append(
                ScoreBucket(
                    label=label,
                    count=len(returns),
                    average_return=sum(returns) / len(returns),
                    hit_rate=sum(1 for value in returns if value > 0) / len(returns),
                )
            )
        else:
            buckets.append(
                ScoreBucket(label=label, count=0, average_return=None, hit_rate=None)
            )

    top = buckets[-1].average_return
    bottom = buckets[0].average_return
    spread = top - bottom if top is not None and bottom is not None else None
    correlation = (
        spearman([score for score, _ in evaluated], [value for _, value in evaluated])
        if len(evaluated) >= 3
        else None
    )

    available = len(evaluated) >= min_samples
    reason = None
    if not available:
        reason = (
            f"Amostra insuficiente: {len(evaluated)} avaliação(ões) madura(s) "
            f"para {min_samples} necessárias. O backtest amadurece {horizon_days} dias "
            "após cada snapshot."
        )

    return BacktestReport(
        snapshots=len(snapshots),
        evaluated=len(evaluated),
        horizon_days=horizon_days,
        buckets=tuple(buckets),
        rank_correlation=correlation,
        top_average=top,
        bottom_average=bottom,
        spread=spread,
        available=available,
        reason=reason,
    )
