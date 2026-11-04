from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.domain.models import Transaction, TransactionType
from src.domain.performance import (
    DatedCashFlow, TwrPeriod, calculate_twr, calculate_xirr, external_cash_flows,
)


def test_twr_removes_external_deposit_effect_and_links_periods():
    result = calculate_twr([
        TwrPeriod(date(2025, 1, 1), date(2025, 7, 1), Decimal("100"),
                  Decimal("220"), Decimal("20")),
        TwrPeriod(date(2025, 7, 1), date(2026, 1, 1), Decimal("200"),
                  Decimal("220"), Decimal("0")),
    ])
    # First subperiod: (220 - 20) / 100 = 2.0; second: 220 / 200 = 1.1.
    assert result.rate == Decimal("1.2")
    assert result.periods == 2


def test_twr_rejects_gaps_and_invalid_flow_adjustment():
    with pytest.raises(ValueError, match="contíguos"):
        calculate_twr([
            TwrPeriod(date(2025, 1, 1), date(2025, 2, 1), Decimal("100"), Decimal("110")),
            TwrPeriod(date(2025, 2, 2), date(2025, 3, 1), Decimal("110"), Decimal("120")),
        ])
    with pytest.raises(ValueError, match="excedem"):
        calculate_twr([
            TwrPeriod(date(2025, 1, 1), date(2025, 2, 1), Decimal("100"), Decimal("10"), Decimal("20"))
        ])


def test_external_cash_flows_exclude_transfers_and_income():
    base = dict(
        portfolio_id="main", occurred_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        institution="Broker", currency="BRL",
    )
    transactions = [
        Transaction(transaction_type=TransactionType.DEPOSIT, amount=Decimal("100"), **base),
        Transaction(transaction_type=TransactionType.WITHDRAWAL, amount=Decimal("25"), **base),
        Transaction(transaction_type=TransactionType.TRANSFER_IN, amount=Decimal("50"), quantity=Decimal("1"),
                    instrument_id="PETR4", **base),
        Transaction(transaction_type=TransactionType.DIVIDEND, amount=Decimal("10"), **base),
    ]
    assert [f.amount for f in external_cash_flows(transactions)] == [Decimal("-100"), Decimal("25")]


def test_xirr_one_year_known_result():
    result = calculate_xirr(
        [DatedCashFlow(date(2025, 1, 1), Decimal("-1000"))],
        terminal_value=Decimal("1100"), terminal_date=date(2026, 1, 1),
    )
    assert float(result) == pytest.approx(0.10, abs=1e-8)


def test_xirr_uses_actual_dates_and_rejects_missing_signs():
    result = calculate_xirr(
        [DatedCashFlow(date(2025, 1, 1), Decimal("-1000"))],
        terminal_value=Decimal("1050"), terminal_date=date(2025, 7, 2),
    )
    assert float(result) > 0.10
    with pytest.raises(ValueError, match="positivo e um negativo"):
        calculate_xirr([], terminal_value=Decimal("100"), terminal_date=date(2025, 1, 1))


def test_xirr_rejects_multiple_roots():
    with pytest.raises(ValueError, match="múltiplas raízes"):
        calculate_xirr([
            DatedCashFlow(date(2020, 1, 1), Decimal("-100")),
            DatedCashFlow(date(2021, 1, 1), Decimal("230")),
            DatedCashFlow(date(2022, 1, 1), Decimal("-132")),
        ], terminal_value=Decimal("0"), terminal_date=date(2022, 1, 1))
