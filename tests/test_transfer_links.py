from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.domain.models import Portfolio, Transaction, TransactionType
from src.persistence.database import SQLiteDatabase
from src.persistence.repositories import PortfolioRepository, TransactionRepository, TransferLinkRepository


def _transfer(tx_id, kind, institution, amount="100"):
    return Transaction(
        id=tx_id, portfolio_id="main", transaction_type=kind,
        occurred_at=datetime(2026, 11, 4, tzinfo=timezone.utc),
        institution=institution, amount=Decimal(amount), currency="BRL",
    )


@pytest.fixture
def repositories(tmp_path):
    db = SQLiteDatabase(tmp_path / "links.db")
    db.initialize()
    PortfolioRepository(db).save(Portfolio(id="main", name="Principal"))
    return TransactionRepository(db), TransferLinkRepository(db)


def test_confirmed_transfer_is_stored_separately_from_immutable_ledger(repositories):
    transactions, links = repositories
    out = _transfer("out-1", TransactionType.TRANSFER_OUT, "Broker A")
    incoming = _transfer("in-1", TransactionType.TRANSFER_IN, "Broker B")
    transactions.append_many([out, incoming])

    link = links.confirm(out.id, incoming.id)
    assert link.transfer_out_id == out.id
    assert link.transfer_in_id == incoming.id
    assert transactions.get(out.id).transfer_id is None
    assert transactions.get(incoming.id).transfer_id is None
    assert links.list_for_portfolio("main") == [link]


def test_transfer_confirmation_rejects_same_direction_and_same_institution(repositories):
    transactions, links = repositories
    out = _transfer("out-1", TransactionType.TRANSFER_OUT, "Broker A")
    other_out = _transfer("out-2", TransactionType.TRANSFER_OUT, "Broker B")
    transactions.append_many([out, other_out])
    with pytest.raises(ValueError, match="TRANSFER_IN"):
        links.confirm(out.id, other_out.id)


def test_transfer_confirmation_is_unique_and_idempotent(repositories):
    transactions, links = repositories
    out = _transfer("out-1", TransactionType.TRANSFER_OUT, "Broker A")
    incoming = _transfer("in-1", TransactionType.TRANSFER_IN, "Broker B")
    transactions.append_many([out, incoming])
    first = links.confirm(out.id, incoming.id)
    assert links.confirm(out.id, incoming.id) == first
    second_incoming = _transfer("in-2", TransactionType.TRANSFER_IN, "Broker C")
    transactions.append(second_incoming)
    with pytest.raises(ValueError, match="já está associado"):
        links.confirm(out.id, second_incoming.id)
