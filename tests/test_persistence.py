from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

from src.domain.models import (
    AssetClass, Instrument, Portfolio, PortfolioPosition, Transaction, TransactionType,
)
from src.persistence.database import SQLiteDatabase
from src.persistence.repositories import (
    InstrumentRepository, PortfolioPositionRepository, PortfolioRepository,
    TransactionRepository,
)


@pytest.fixture
def database(tmp_path):
    db = SQLiteDatabase(tmp_path / "portfolio.db")
    db.initialize()
    return db


def test_migrations_are_versioned_and_idempotent(tmp_path):
    db = SQLiteDatabase(tmp_path / "nested" / "portfolio.db")
    db.initialize()
    db.initialize()
    assert db.applied_migrations() == [
        (1, "0001_initial_schema.sql"),
        (2, "0002_transaction_sequence.sql"),
    ]


def test_portfolio_and_instrument_round_trip(database):
    portfolio_repo = PortfolioRepository(database)
    instrument_repo = InstrumentRepository(database)
    portfolio = Portfolio(id="main", name="Principal")
    instrument = Instrument(
        id="asset-1", name="Fundo Imobiliário", asset_class=AssetClass.FII,
        currency="brl", provider_symbols={"market": "ABCD11"},
        metadata={"segment": "logística"},
    )
    portfolio_repo.save(portfolio)
    instrument_repo.save(instrument)
    assert portfolio_repo.get("main") == portfolio
    assert instrument_repo.get("asset-1") == instrument
    assert instrument_repo.list_all() == [instrument]


def test_position_snapshot_round_trip_and_upsert(database):
    PortfolioRepository(database).save(Portfolio(id="main", name="Principal"))
    InstrumentRepository(database).save(
        Instrument(id="asset-1", name="Ativo", asset_class=AssetClass.EQUITY, currency="BRL")
    )
    repo = PortfolioPositionRepository(database)
    position = PortfolioPosition(
        portfolio_id="main", instrument_id="asset-1", institution="Corretora",
        quantity=Decimal("12.5000"), average_cost=Decimal("101.23456789"),
        cost_currency="brl", as_of=date(2026, 11, 4),
    )
    repo.save_snapshot(position)
    repo.save_snapshot(position.model_copy(update={"quantity": Decimal("13.5")}))
    rows = repo.list_snapshots("main")
    assert len(rows) == 1
    assert rows[0].quantity == Decimal("13.5")
    assert rows[0].average_cost == Decimal("101.23456789")


def test_transaction_append_round_trip_preserves_decimal_precision(database):
    PortfolioRepository(database).save(Portfolio(id="main", name="Principal"))
    InstrumentRepository(database).save(
        Instrument(id="asset-1", name="Ativo", asset_class=AssetClass.EQUITY, currency="BRL")
    )
    transaction = Transaction(
        id="tx-1", portfolio_id="main", transaction_type=TransactionType.BUY,
        occurred_at=datetime(2026, 11, 4, 13, 30, tzinfo=timezone.utc), sequence=3,
        institution="Corretora", instrument_id="asset-1", quantity=Decimal("0.12345678"),
        unit_price=Decimal("123.45678901"), amount=Decimal("15.241578"), currency="brl",
        fees=Decimal("0.01"), taxes=Decimal("0"), metadata={"source": "manual"},
    )
    repo = TransactionRepository(database)
    repo.append(transaction)
    assert repo.get("tx-1") == transaction
    assert repo.list_for_portfolio("main", instrument_id="asset-1") == [transaction]


def test_transactions_are_append_only_and_external_ids_are_idempotency_keys(database):
    PortfolioRepository(database).save(Portfolio(id="main", name="Principal"))
    transaction = Transaction(
        id="tx-1", portfolio_id="main", transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc), institution="Banco",
        amount=Decimal("500"), currency="BRL", external_id="bank-row-42",
    )
    repo = TransactionRepository(database)
    repo.append(transaction)
    with pytest.raises(sqlite3.IntegrityError):
        repo.append(transaction.model_copy(update={"id": "tx-2"}))
    assert repo.get("tx-1") == transaction
    assert repo.get("tx-2") is None


def test_foreign_keys_prevent_orphan_transactions(database):
    transaction = Transaction(
        id="tx-1", portfolio_id="missing", transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc), institution="Banco",
        amount=Decimal("100"), currency="BRL",
    )
    with pytest.raises(sqlite3.IntegrityError):
        TransactionRepository(database).append(transaction)


def test_transfer_event_round_trips_pairing_reference(database):
    PortfolioRepository(database).save(Portfolio(id="main", name="Principal"))
    transaction = Transaction(
        id="transfer-in", portfolio_id="main", transaction_type=TransactionType.TRANSFER_IN,
        occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc), institution="Banco B",
        amount=Decimal("250"), currency="BRL", transfer_id="move-123",
    )
    repo = TransactionRepository(database)
    repo.append(transaction)
    assert repo.get("transfer-in").transfer_id == "move-123"


def test_transaction_timestamps_are_stored_and_sorted_as_utc(database):
    PortfolioRepository(database).save(Portfolio(id="main", name="Principal"))
    repo = TransactionRepository(database)
    later_instant = Transaction(
        id="later", portfolio_id="main", transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime.fromisoformat("2026-11-04T12:00:00-03:00"),
        institution="Banco", amount=Decimal("10"), currency="BRL",
    )
    earlier_instant = Transaction(
        id="earlier", portfolio_id="main", transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime.fromisoformat("2026-11-04T13:00:00+00:00"),
        institution="Banco", amount=Decimal("10"), currency="BRL",
    )
    repo.append(later_instant)
    repo.append(earlier_instant)
    assert [tx.id for tx in repo.list_for_portfolio("main")] == ["earlier", "later"]
    assert repo.get("later").occurred_at == datetime.fromisoformat("2026-11-04T15:00:00+00:00")


def test_same_timestamp_transactions_use_explicit_sequence(database):
    PortfolioRepository(database).save(Portfolio(id="main", name="Principal"))
    repo = TransactionRepository(database)
    later_sequence = Transaction(
        id="event-2", portfolio_id="main", transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc), sequence=2,
        institution="Banco", amount=Decimal("20"), currency="BRL",
    )
    earlier_sequence = later_sequence.model_copy(update={"id": "event-1", "sequence": 1})
    repo.append(later_sequence)
    repo.append(earlier_sequence)
    assert [tx.id for tx in repo.list_for_portfolio("main")] == ["event-1", "event-2"]
