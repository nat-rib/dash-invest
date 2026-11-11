"""Rotas do motor de risco (Fase 4)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.dependencies import Repositories as RepositoryBundle
from api.dependencies import get_repositories
from api.schemas.risk import RiskReportOut
from api.services import risk_service

router = APIRouter(prefix="/api", tags=["risk"])

Repositories = Annotated[RepositoryBundle, Depends(get_repositories)]


def _out(report) -> RiskReportOut:
    return RiskReportOut(
        observations=report.observations,
        returns=report.returns,
        start_date=report.start_date,
        end_date=report.end_date,
        total_return=report.total_return,
        annualized_volatility=report.annualized_volatility,
        max_drawdown=report.max_drawdown,
        sharpe=report.sharpe,
        sortino=report.sortino,
        var_95=report.var_95,
        cvar_95=report.cvar_95,
        var_95_parametric=report.var_95_parametric,
        cvar_95_parametric=report.cvar_95_parametric,
        beta=report.beta,
        correlation=report.correlation,
        monthly_returns=[
            {"month": item.month, "return_value": item.return_value}
            for item in report.monthly_returns
        ],
        unavailable=list(report.unavailable),
        reason=report.reason,
    )


@router.get("/risk/instrument", response_model=RiskReportOut)
def instrument_risk(
    repositories: Repositories,
    provider: str = Query(...),
    instrument_id: str = Query(...),
    metric: str = Query("close"),
    risk_free_rate: float = Query(0.0, ge=-1.0, le=2.0),
    benchmark_provider: str | None = Query(default=None),
    benchmark_instrument_id: str | None = Query(default=None),
) -> RiskReportOut:
    report = risk_service.instrument_report(
        repositories,
        provider=provider,
        instrument_id=instrument_id,
        metric=metric,
        risk_free_rate=risk_free_rate,
        benchmark_provider=benchmark_provider,
        benchmark_instrument_id=benchmark_instrument_id,
    )
    return _out(report)


@router.get("/risk/portfolio", response_model=RiskReportOut)
def portfolio_risk(
    risk_free_rate: float = Query(0.0, ge=-1.0, le=2.0),
) -> RiskReportOut:
    return _out(risk_service.portfolio_report(risk_free_rate=risk_free_rate))
