"""Contratos do motor de risco (Fase 4)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class MonthlyReturnOut(BaseModel):
    month: str
    return_value: float


class RiskReportOut(BaseModel):
    observations: int
    returns: int
    start_date: date | None = None
    end_date: date | None = None
    total_return: float | None = None
    annualized_volatility: float | None = None
    max_drawdown: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    var_95: float | None = None
    cvar_95: float | None = None
    var_95_parametric: float | None = None
    cvar_95_parametric: float | None = None
    beta: float | None = None
    correlation: float | None = None
    monthly_returns: list[MonthlyReturnOut] = []
    unavailable: list[str] = []
    reason: str | None = None
