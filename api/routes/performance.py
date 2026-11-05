"""Rotas do domínio Rentabilidade (Fase 2 do roadmap)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.config import default_portfolio_id
from api.dependencies import get_repositories
from api.schemas.performance import (
    PerformanceFlowsOut, PerformanceFlowOut, TwrCalculateIn, TwrCalculateOut,
    TwrPeriodIn, TwrPeriodOut, TwrValuationsOut, TwrValuationsSaveIn,
    XirrCalculateIn, XirrCalculateOut,
)
from api.services import performance_service
from api.services.ledger_service import LedgerValidationError
from src.persistence.repositories import PerformancePeriod

router = APIRouter(prefix="/api/performance", tags=["performance"])
Repositories = Annotated[object, Depends(get_repositories)]


def _bad_request(message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail=message)


def _portfolio_id(value: str | None) -> str:
    return value or default_portfolio_id()


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise _bad_request(f"Data inválida: {value!r}; informe AAAA-MM-DD.") from error


def _decimal(value: str, *, label: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise _bad_request(f"{label} não é um decimal válido.") from error
    if not parsed.is_finite():
        raise _bad_request(f"{label} deve ser finito.")
    return parsed


# ---------------------------------------------------------------- fluxos

@router.get("/flows", response_model=PerformanceFlowsOut)
def external_flows(repositories: Repositories, portfolio_id: str = Query(default="")) -> PerformanceFlowsOut:
    pid = _portfolio_id(portfolio_id)
    try:
        flows, currency, reason = performance_service.external_flows(
            repositories.portfolios, repositories.transactions, portfolio_id=pid,
        )
    except LedgerValidationError as error:
        raise _bad_request(str(error)) from error
    outcome = PerformanceFlowsOut(
        portfolio_id=pid,
        portfolio_name=repositories.portfolios.get(pid).name,
        currency=currency,
        flows=[
            PerformanceFlowOut(date=flow.date.isoformat(), amount=str(flow.amount), currency=currency)
            for flow in flows
        ],
        unavailable_reason=reason,
    )
    return outcome


# ---------------------------------------------------------------- XIRR

@router.post("/xirr/calculate", response_model=XirrCalculateOut)
def xirr_calculate(repositories: Repositories, body: XirrCalculateIn) -> XirrCalculateOut:
    pid = _portfolio_id(body.portfolio_id)
    try:
        flows, currency, reason = performance_service.external_flows(
            repositories.portfolios, repositories.transactions, portfolio_id=pid,
        )
    except LedgerValidationError as error:
        raise _bad_request(str(error)) from error
    if reason:
        raise _bad_request(f"XIRR indisponível: {reason}", status_code=422)
    terminal_date = _date(body.terminal_date)
    terminal_value = _decimal(body.terminal_value, label="terminal_value")
    if terminal_value < 0:
        raise _bad_request("O valor terminal não pode ser negativo.")
    try:
        rate = performance_service.calculate_xirr(
            flows, terminal_value=terminal_value, terminal_date=terminal_date,
        )
    except (ValueError, ArithmeticError) as error:
        raise _bad_request(f"XIRR indisponível: {error}", status_code=422) from error
    return XirrCalculateOut(
        annual_rate=str(rate),
        terminal_value=str(terminal_value),
        terminal_date=terminal_date.isoformat(),
        flows_used=len(flows),
    )


# ---------------------------------------------------------------- TWR

def _period_rows(rows: list[TwrPeriodIn], *, portfolio_id: str, currency: str) -> list[PerformancePeriod]:
    built: list[PerformancePeriod] = []
    for row in rows:
        start_value = _decimal(row.start_value, label="start_value")
        end_value = _decimal(row.end_value_after_flows, label="end_value_after_flows")
        net_flow = _decimal(row.net_external_flow, label="net_external_flow")
        if start_value <= 0:
            raise _bad_request("O valor inicial do período deve ser positivo.")
        if end_value < 0:
            raise _bad_request("O valor final não pode ser negativo.")
        built.append(PerformancePeriod(
            portfolio_id=portfolio_id,
            start_date=_date(row.start_date),
            end_date=_date(row.end_date),
            start_value=start_value,
            end_value_after_flows=end_value,
            net_external_flow=net_flow,
            currency=currency,
        ))
    return built


@router.get("/twr", response_model=TwrValuationsOut)
def twr_valuations(repositories: Repositories, portfolio_id: str = Query(default="")) -> TwrValuationsOut:
    pid = _portfolio_id(portfolio_id)
    try:
        portfolio, currency = performance_service.require_portfolio(repositories.portfolios, pid)
    except LedgerValidationError as error:
        raise _bad_request(str(error)) from error
    stored = performance_service.stored_periods(repositories.performance_periods, pid)
    return TwrValuationsOut(
        portfolio_id=portfolio,
        currency=currency,
        periods=[
            TwrPeriodOut(
                start_date=row.start_date.isoformat(),
                end_date=row.end_date.isoformat(),
                start_value=str(row.start_value),
                end_value_after_flows=str(row.end_value_after_flows),
                net_external_flow=str(row.net_external_flow),
            )
            for row in stored
        ],
        saved=len(stored),
    )


@router.post("/valuations", response_model=TwrValuationsOut)
def save_valuations(repositories: Repositories, body: TwrValuationsSaveIn) -> TwrValuationsOut:
    pid = _portfolio_id(body.portfolio_id)
    try:
        portfolio, currency = performance_service.require_portfolio(repositories.portfolios, pid)
    except LedgerValidationError as error:
        raise _bad_request(str(error)) from error
    currency = (body.currency or currency).upper()
    rows = _period_rows(body.periods, portfolio_id=pid, currency=currency)
    saved = performance_service.save_periods(
        repositories.performance_periods, portfolio_id=pid, rows=rows,
    )
    return TwrValuationsOut(
        portfolio_id=portfolio,
        currency=currency,
        periods=[
            TwrPeriodOut(
                start_date=row.start_date.isoformat(),
                end_date=row.end_date.isoformat(),
                start_value=str(row.start_value),
                end_value_after_flows=str(row.end_value_after_flows),
                net_external_flow=str(row.net_external_flow),
            )
            for row in rows
        ],
        saved=saved,
    )


@router.post("/twr/calculate", response_model=TwrCalculateOut)
def twr_calculate(repositories: Repositories, body: TwrCalculateIn) -> TwrCalculateOut:
    pid = _portfolio_id(body.portfolio_id)
    try:
        portfolio, currency = performance_service.require_portfolio(repositories.portfolios, pid)
    except LedgerValidationError as error:
        raise _bad_request(str(error)) from error
    if body.periods is None:
        stored = performance_service.stored_periods(repositories.performance_periods, pid)
    else:
        if not body.periods:
            raise _bad_request("Informe ao menos um período TWR.")
        stored = _period_rows(body.periods, portfolio_id=pid, currency=currency)
    if not stored:
        raise _bad_request(
            "TWR indisponível: cadastre períodos avaliados ou informe-os na requisição.",
            status_code=422,
        )
    try:
        result = performance_service.calculate_twr(performance_service.domain_periods_from(stored))
    except ValueError as error:
        raise _bad_request(f"TWR indisponível: {error}", status_code=422) from error
    return TwrCalculateOut(
        rate=str(result.rate),
        periods=result.periods,
        start_date=result.start_date.isoformat(),
        end_date=result.end_date.isoformat(),
    )
