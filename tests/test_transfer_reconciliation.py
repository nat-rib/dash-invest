from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.domain.models import Transaction, TransactionType
from src.domain.reconciliation import reconcile_transfers


def event(event_id, kind, institution, day=4, *, amount="100", transfer_id=None):
    return Transaction(
        id=event_id, portfolio_id="main", transaction_type=kind,
        occurred_at=datetime(2026, 11, day, 12, tzinfo=timezone.utc),
        institution=institution, amount=Decimal(amount), currency="BRL",
        transfer_id=transfer_id,
    )


def test_suggests_unique_unlinked_cash_transfer_pair():
    out = event("out-1", TransactionType.TRANSFER_OUT, "Banco A")
    incoming = event("in-1", TransactionType.TRANSFER_IN, "Banco B", day=5)
    result = reconcile_transfers([out, incoming])
    assert [(p.transfer_out_id, p.transfer_in_id) for p in result.suggested_pairs] == [("out-1", "in-1")]
    assert result.unmatched_transaction_ids == ()


def test_does_not_auto_suggest_ambiguous_transfer():
    out = event("out-1", TransactionType.TRANSFER_OUT, "Banco A")
    in_a = event("in-1", TransactionType.TRANSFER_IN, "Banco B")
    in_b = event("in-2", TransactionType.TRANSFER_IN, "Banco C")
    result = reconcile_transfers([out, in_a, in_b])
    assert result.suggested_pairs == ()
    assert set(result.ambiguous_transaction_ids) == {"out-1", "in-1", "in-2"}


def test_explicit_transfer_id_is_confirmed_only_if_economics_match():
    out = event("out-1", TransactionType.TRANSFER_OUT, "Banco A", day=4, transfer_id="move-1")
    incoming = event("in-1", TransactionType.TRANSFER_IN, "Banco B", day=20, transfer_id="move-1")
    result = reconcile_transfers([out, incoming])
    assert len(result.confirmed_pairs) == 1
    assert result.invalid_transfer_ids == ()


def test_explicit_transfer_id_with_mismatched_amount_is_invalid():
    out = event("out-1", TransactionType.TRANSFER_OUT, "Banco A", transfer_id="move-1")
    incoming = event("in-1", TransactionType.TRANSFER_IN, "Banco B", amount="90", transfer_id="move-1")
    result = reconcile_transfers([out, incoming])
    assert result.invalid_transfer_ids == ("move-1",)


def test_unmatched_and_incomplete_events_are_reported():
    out = event("out-1", TransactionType.TRANSFER_OUT, "Banco A", amount="1000")
    result = reconcile_transfers([out])
    assert result.unmatched_transaction_ids == ("out-1",)
    linked = event("out-2", TransactionType.TRANSFER_OUT, "Banco A", transfer_id="pending")
    assert reconcile_transfers([linked]).incomplete_transfer_ids == ("pending",)


def test_different_amounts_are_not_candidates():
    out = event("out-1", TransactionType.TRANSFER_OUT, "Banco A")
    incoming = event("in-1", TransactionType.TRANSFER_IN, "Banco B", amount="200")
    result = reconcile_transfers([out, incoming])
    assert result.suggested_pairs == ()
    assert set(result.unmatched_transaction_ids) == {"out-1", "in-1"}
