"""Motor de risco determinístico sobre séries de preço.

Regras:
- retornos simples diários (`P_t / P_{t-1} - 1`), base de 252 dias úteis;
- amostra insuficiente retorna indisponível, nunca zero;
- VaR/CVaR históricos reportados como perda positiva (fração do patrimônio);
- beta/correlação exigem benchmark alinhado por data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

TRADING_DAYS = 252
MIN_RETURNS = 20
VAR_CONFIDENCE = 0.95


@dataclass(frozen=True)
class PricePoint:
    day: date
    value: float


@dataclass(frozen=True)
class MonthlyReturn:
    month: str
    return_value: float


@dataclass(frozen=True)
class RiskReport:
    observations: int
    returns: int
    start_date: date | None
    end_date: date | None
    total_return: float | None
    annualized_volatility: float | None
    max_drawdown: float | None
    sharpe: float | None
    sortino: float | None
    var_95: float | None
    cvar_95: float | None
    var_95_parametric: float | None
    cvar_95_parametric: float | None
    beta: float | None
    correlation: float | None
    monthly_returns: tuple[MonthlyReturn, ...]
    unavailable: tuple[str, ...]
    reason: str | None


def _clean(points: Sequence[PricePoint]) -> list[tuple[date, float]]:
    dedup: dict[date, float] = {}
    for point in points:
        value = float(point.value)
        if math.isfinite(value) and value > 0:
            dedup[point.day] = value
    return [(day, dedup[day]) for day in sorted(dedup)]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _covariance(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) < 2 or len(left) != len(right):
        return 0.0
    left_mean, right_mean = _mean(left), _mean(right)
    return sum(
        (a - left_mean) * (b - right_mean) for a, b in zip(left, right)
    ) / (len(left) - 1)


def percentile(values: Sequence[float], quantile: float) -> float | None:
    """Percentil com interpolação linear, sem dependência de numpy."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _returns(values: Sequence[float]) -> list[float]:
    return [values[index] / values[index - 1] - 1 for index in range(1, len(values))]


def _max_drawdown(values: Sequence[float]) -> float:
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1)
    return worst


def _monthly_returns_from_clean(
    cleaned: Sequence[tuple[date, float]],
) -> list[MonthlyReturn]:
    last_by_month: dict[str, float] = {}
    for day, value in cleaned:
        last_by_month[day.strftime("%Y-%m")] = value

    results: list[MonthlyReturn] = []
    previous: float | None = None
    for month in sorted(last_by_month):
        current = last_by_month[month]
        if previous is not None and previous > 0:
            results.append(MonthlyReturn(month=month, return_value=current / previous - 1))
        previous = current
    return results


def monthly_returns(points: Sequence[PricePoint]) -> list[MonthlyReturn]:
    """Retorno mês a mês usando o último preço observado em cada mês."""
    return _monthly_returns_from_clean(_clean(points))


def return_series(points: Sequence[PricePoint]) -> list[tuple[date, float]]:
    """Retornos diários alinhados à data do preço de fechamento."""
    cleaned = _clean(points)
    return [
        (cleaned[index][0], cleaned[index][1] / cleaned[index - 1][1] - 1)
        for index in range(1, len(cleaned))
    ]


def correlation(left: Sequence[PricePoint], right: Sequence[PricePoint]) -> float | None:
    """Correlação de Pearson entre retornos diários alinhados por data."""
    left_returns = dict(return_series(left))
    right_returns = dict(return_series(right))
    common = sorted(set(left_returns) & set(right_returns))
    if len(common) < MIN_RETURNS:
        return None
    left_values = [left_returns[day] for day in common]
    right_values = [right_returns[day] for day in common]
    denominator = _std(left_values) * _std(right_values)
    if denominator == 0:
        return None
    return _covariance(left_values, right_values) / denominator


def calculate_risk(
    points: Sequence[PricePoint],
    *,
    risk_free_rate: float = 0.0,
    benchmark: Sequence[PricePoint] | None = None,
) -> RiskReport:
    cleaned = _clean(points)
    unavailable: list[str] = []

    if len(cleaned) < 2:
        return RiskReport(
            observations=len(cleaned),
            returns=0,
            start_date=cleaned[0][0] if cleaned else None,
            end_date=cleaned[-1][0] if cleaned else None,
            total_return=None,
            annualized_volatility=None,
            max_drawdown=None,
            sharpe=None,
            sortino=None,
            var_95=None,
            cvar_95=None,
            var_95_parametric=None,
            cvar_95_parametric=None,
            beta=None,
            correlation=None,
            monthly_returns=(),
            unavailable=("total_return", "annualized_volatility", "max_drawdown", "sharpe", "sortino", "var_95", "cvar_95"),
            reason="São necessários ao menos dois preços válidos.",
        )

    values = [value for _, value in cleaned]
    returns = _returns(values)
    total_return = values[-1] / values[0] - 1
    max_drawdown = _max_drawdown(values)

    annualized_volatility = None
    sharpe = None
    sortino = None
    var_95 = None
    cvar_95 = None
    var_95_parametric = None
    cvar_95_parametric = None

    if len(returns) >= MIN_RETURNS:
        volatility = _std(returns)
        annualized_volatility = volatility * math.sqrt(TRADING_DAYS)
        daily_risk_free = risk_free_rate / TRADING_DAYS
        excess = _mean(returns) - daily_risk_free
        if volatility > 0:
            sharpe = excess / volatility * math.sqrt(TRADING_DAYS)
        downside = math.sqrt(_mean([min(value, 0.0) ** 2 for value in returns]))
        if downside > 0:
            sortino = excess / downside * math.sqrt(TRADING_DAYS)
        cutoff = percentile(returns, 1 - VAR_CONFIDENCE)
        if cutoff is not None:
            var_95 = max(0.0, -cutoff)
            tail = [value for value in returns if value <= cutoff]
            cvar_95 = max(0.0, -_mean(tail)) if tail else var_95
        mean_return = _mean(returns)
        z_score = 1.6448536269514722
        var_95_parametric = max(0.0, -(mean_return - z_score * volatility))
        density = math.exp(-z_score * z_score / 2) / math.sqrt(2 * math.pi)
        cvar_95_parametric = max(
            0.0,
            -(mean_return - volatility * density / (1 - VAR_CONFIDENCE)),
        )
    else:
        unavailable.extend(
            [
                "annualized_volatility",
                "sharpe",
                "sortino",
                "var_95",
                "cvar_95",
                "var_95_parametric",
                "cvar_95_parametric",
            ]
        )

    beta = None
    correlation = None
    if benchmark is not None:
        asset_map = dict(cleaned)
        benchmark_values = dict(_clean(benchmark))
        common_days = [day for day, _ in cleaned if day in benchmark_values]
        if len(common_days) >= MIN_RETURNS + 1:
            asset_series = [asset_map[day] for day in common_days]
            benchmark_series = [benchmark_values[day] for day in common_days]
            asset_returns = _returns(asset_series)
            benchmark_returns = _returns(benchmark_series)
            benchmark_variance = _std(benchmark_returns) ** 2
            if benchmark_variance > 0:
                beta = _covariance(asset_returns, benchmark_returns) / benchmark_variance
                denominator = _std(asset_returns) * _std(benchmark_returns)
                if denominator > 0:
                    correlation = _covariance(asset_returns, benchmark_returns) / denominator
        else:
            unavailable.extend(["beta", "correlation"])

    return RiskReport(
        observations=len(cleaned),
        returns=len(returns),
        start_date=cleaned[0][0],
        end_date=cleaned[-1][0],
        total_return=total_return,
        annualized_volatility=annualized_volatility,
        max_drawdown=max_drawdown,
        sharpe=sharpe,
        sortino=sortino,
        var_95=var_95,
        cvar_95=cvar_95,
        var_95_parametric=var_95_parametric,
        cvar_95_parametric=cvar_95_parametric,
        beta=beta,
        correlation=correlation,
        monthly_returns=tuple(_monthly_returns_from_clean(cleaned)),
        unavailable=tuple(unavailable),
        reason=None,
    )
