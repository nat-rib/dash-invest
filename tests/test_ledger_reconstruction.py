from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.domain.ledger import (
    IncompleteOpeningPositionError, InsufficientPositionError, rebuild_position,
)
from src.domain.models import PortfolioPosition, Transaction, TransactionType


def _tx(tx_id, kind, *, institution="Broker", quantity=None, unit_price=None,
        amount=None, fees="0", taxes="0", metadata=None, transfer_id=None):
    return Transaction(
        id=tx_id, portfolio_id="main", transaction_type=kind,
        occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
        institution=institution, instrument_id="asset-1", quantity=quantity,
        unit_price=unit_price, amount=amount, currency="BRL", fees=Decimal(fees),
        taxes=Decimal(taxes), metadata=metadata or {}, transfer_id=transfer_id,
    )


def test_buy_sell_reconstructs_weighted_average_cost_and_realized_profit():
    result = rebuild_position(
        portfolio_id="main", instrument_id="asset-1", institution="Broker",
        transactions=[
            _tx("buy-1", TransactionType.BUY, quantity=Decimal("10"), unit_price=Decimal("100"), fees="10"),
            _tx("buy-2", TransactionType.BUY, quantity=Decimal("5"), unit_price=Decimal("120"), fees="5"),
            _tx("sell-1", TransactionType.SELL, quantity=Decimal("4"), unit_price=Decimal("130"), fees="2"),
        ],
    )
    assert result.position.quantity == Decimal("11")
    assert result.cost_basis == Decimal("1615") - (Decimal("1615") / Decimal("15")) * Decimal("4")
    assert result.position.average_cost == result.cost_basis / Decimal("11")
    assert result.realized_profit == Decimal("518") - (Decimal("1615") / Decimal("15")) * Decimal("4")
    assert result.transactions_applied == 3


def test_sell_cannot_exceed_available_quantity():
    with pytest.raises(InsufficientPositionError):
        rebuild_position(
            portfolio_id="main", instrument_id="asset-1", institution="Broker",
            transactions=[_tx("sell", TransactionType.SELL, quantity=Decimal("1"), unit_price=Decimal("10"))],
        )


def test_split_and_bonus_change_quantity_without_changing_cost_basis():
    opening = PortfolioPosition(
        portfolio_id="main", instrument_id="asset-1", institution="Broker",
        quantity=Decimal("10"), average_cost=Decimal("100"),
        cost_currency="BRL", as_of=date(2026, 11, 3),
    )
    result = rebuild_position(
        portfolio_id="main", instrument_id="asset-1", institution="Broker",
        opening_position=opening,
        transactions=[
            _tx("split", TransactionType.SPLIT, metadata={"ratio": "2"}),
            _tx("bonus", TransactionType.BONUS, quantity=Decimal("5")),
        ],
    )
    assert result.position.quantity == Decimal("25")
    assert result.cost_basis == Decimal("1000")
    assert result.position.average_cost == Decimal("40")


def test_amortization_reduces_cost_basis_and_income_does_not_change_quantity():
    opening = PortfolioPosition(
        portfolio_id="main", instrument_id="asset-1", institution="Broker",
        quantity=Decimal("10"), average_cost=Decimal("100"),
        cost_currency="BRL", as_of=date(2026, 11, 3),
    )
    result = rebuild_position(
        portfolio_id="main", instrument_id="asset-1", institution="Broker",
        opening_position=opening,
        transactions=[
            _tx("amort", TransactionType.AMORTIZATION, amount=Decimal("100")),
            _tx("div", TransactionType.DIVIDEND, amount=Decimal("50")),
        ],
    )
    assert result.position.quantity == Decimal("10")
    assert result.cost_basis == Decimal("900")
    assert result.position.average_cost == Decimal("90")


def test_asset_transfer_preserves_total_position_and_cost_basis_between_institutions():
    opening = PortfolioPosition(
        portfolio_id="main", instrument_id="asset-1", institution="Broker A",
        quantity=Decimal("10"), average_cost=Decimal("100"),
        cost_currency="BRL", as_of=date(2026, 11, 3),
    )
    out = rebuild_position(
        portfolio_id="main", instrument_id="asset-1", institution="Broker A",
        opening_position=opening,
        transactions=[_tx("out", TransactionType.TRANSFER_OUT, institution="Broker A",
                          quantity=Decimal("4"), amount=Decimal("400"), transfer_id="move-1")],
    )
    incoming = rebuild_position(
        portfolio_id="main", instrument_id="asset-1", institution="Broker B",
        transactions=[_tx("in", TransactionType.TRANSFER_IN, institution="Broker B",
                          quantity=Decimal("4"), amount=Decimal("400"), transfer_id="move-1")],
    )
    assert out.position.quantity + incoming.position.quantity == Decimal("10")
    assert out.cost_basis + incoming.cost_basis == Decimal("1000")


def test_unknown_opening_quantity_is_not_assumed_to_be_zero():
    opening = PortfolioPosition(
        portfolio_id="main", instrument_id="asset-1", institution="Broker",
        quantity=None, average_cost=None, cost_currency="BRL", as_of=date(2026, 11, 3),
    )
    with pytest.raises(IncompleteOpeningPositionError):
        rebuild_position(
            portfolio_id="main", instrument_id="asset-1", institution="Broker",
            opening_position=opening, transactions=[],
        )


def test_split_requires_positive_ratio_and_asset_transfer_requires_cost_basis():
    with pytest.raises(ValidationError, match="metadata.ratio"):
        _tx("split", TransactionType.SPLIT)
    with pytest.raises(ValidationError, match="amount"):
        _tx("transfer", TransactionType.TRANSFER_IN, quantity=Decimal("1"), transfer_id="move")
