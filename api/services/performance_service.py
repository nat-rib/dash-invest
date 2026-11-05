"""Serviço de rentabilidade: fluxos externos, XIRR e TWR.

Reutiliza integralmente src.domain.performance; indisponibilidades de cálculo
voltam como explicações acionáveis, nunca como valores estimados.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.domain import performance
from src.persistence.repositories import (
    PerformancePeriod, PerformancePeriodRepository, PortfolioRepository,
    TransactionRepository,
)

from api.services.ledger_service import LedgerValidationError


def require_portfolio(portfolios: PortfolioRepository, portfolio_id: str) -> tuple[str, str]:
    portfolio = portfolios.get(portfolio_id)
    if portfolio is None:
        raise LedgerValidationError(
            "A carteira SQLite ainda não existe; migre o snapshot JSON primeiro."
        )
    return portfolio.id, portfolio.base_currency


def external_flows(
    portfolios: PortfolioRepository, transactions: TransactionRepository, *,
    portfolio_id: str,
) -> tuple[list[performance.DatedCashFlow], str, str | None]:
    """Fluxos externos na moeda-base; mistura cambial vira motivo explícito, não erro HTTP."""
    portfolio, base_currency = require_portfolio(portfolios, portfolio_id)
    items = transactions.list_for_portfolio(portfolio)
    try:
        flows = list(performance.external_cash_flows(items, currency=base_currency))
    except ValueError as error:
        return [], base_currency, str(error)
    return flows, base_currency, None


def calculate_xirr(
    flows: list[performance.DatedCashFlow], *, terminal_value: Decimal, terminal_date: date,
) -> Decimal:
    return performance.calculate_xirr(
        flows, terminal_value=terminal_value, terminal_date=terminal_date,
    )


def domain_periods_from(rows: list[PerformancePeriod]) -> list[performance.TwrPeriod]:
    return [row.to_domain_period() for row in rows]


def calculate_twr(rows: list[performance.TwrPeriod]) -> performance.PerformanceResult:
    return performance.calculate_twr(rows)


def stored_periods(repository: PerformancePeriodRepository, portfolio_id: str) -> list[PerformancePeriod]:
    return repository.list_for_portfolio(portfolio_id)


def save_periods(
    repository: PerformancePeriodRepository, *, portfolio_id: str,
    rows: list[PerformancePeriod],
) -> int:
    return repository.replace_all(portfolio_id, rows)
