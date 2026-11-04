from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.domain.models import (
    AssetClass, Instrument, PortfolioPosition, Transaction, TransactionType,
)


def test_instrument_has_internal_identity_and_normalized_currency():
    instrument = Instrument(name="Apple Inc.", asset_class=AssetClass.EQUITY, currency="usd")
    assert instrument.id
    assert instrument.currency == "USD"
    assert instrument.provider_symbols == {}


def test_portfolio_position_is_separate_from_instrument():
    position = PortfolioPosition(
        portfolio_id="main", instrument_id="instrument-1", institution="Broker",
        quantity=Decimal("2.5"), average_cost=Decimal("100"),
        cost_currency="usd", as_of=date(2026, 11, 4),
    )
    assert position.instrument_id == "instrument-1"
    assert position.cost_currency == "USD"


def test_buy_requires_instrument_quantity_and_unit_price():
    with pytest.raises(ValidationError, match="BUY/SELL exigem"):
        Transaction(
            portfolio_id="main", transaction_type=TransactionType.BUY,
            occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
            institution="Broker", currency="BRL",
        )


def test_cash_event_requires_amount():
    with pytest.raises(ValidationError, match="exige amount"):
        Transaction(
            portfolio_id="main", transaction_type=TransactionType.DIVIDEND,
            occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
            institution="Broker", instrument_id="asset-1", currency="BRL",
        )


def test_internal_transfer_requires_pairing_reference():
    with pytest.raises(ValidationError, match="transfer_id"):
        Transaction(
            portfolio_id="main", transaction_type=TransactionType.TRANSFER_OUT,
            occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
            institution="Broker", amount=Decimal("100"), currency="BRL",
        )


def test_internal_transfer_accepts_shared_reference():
    tx = Transaction(
        portfolio_id="main", transaction_type=TransactionType.TRANSFER_IN,
        occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
        institution="New broker", amount=Decimal("100"), currency="BRL",
        transfer_id="transfer-123",
    )
    assert tx.transfer_id == "transfer-123"


def test_transaction_timestamp_must_be_timezone_aware():
    with pytest.raises(ValidationError, match="timezone"):
        Transaction(
            portfolio_id="main", transaction_type=TransactionType.DEPOSIT,
            occurred_at=datetime(2026, 11, 4), institution="Broker",
            amount=Decimal("100"), currency="BRL",
        )


def test_transaction_amounts_must_be_positive():
    with pytest.raises(ValidationError):
        Transaction(
            portfolio_id="main", transaction_type=TransactionType.DEPOSIT,
            occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
            institution="Broker", amount=Decimal("0"), currency="BRL",
        )
