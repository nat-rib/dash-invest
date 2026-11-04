"""Sugestões conservadoras de pareamento de transferências internas."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Iterable

from src.domain.models import Transaction, TransactionType


@dataclass(frozen=True)
class TransferPair:
    transfer_out_id: str
    transfer_in_id: str
    date_delta: timedelta
    amount_delta: Decimal


@dataclass(frozen=True)
class TransferReconciliation:
    confirmed_pairs: tuple[TransferPair, ...]
    suggested_pairs: tuple[TransferPair, ...]
    ambiguous_transaction_ids: tuple[str, ...]
    unmatched_transaction_ids: tuple[str, ...]
    incomplete_transfer_ids: tuple[str, ...]
    invalid_transfer_ids: tuple[str, ...]


def _economically_compatible(
    outbound: Transaction,
    inbound: Transaction,
    *,
    amount_tolerance: Decimal,
    quantity_tolerance: Decimal,
    date_window: timedelta,
) -> bool:
    if outbound.transaction_type != TransactionType.TRANSFER_OUT:
        return False
    if inbound.transaction_type != TransactionType.TRANSFER_IN:
        return False
    if outbound.portfolio_id != inbound.portfolio_id:
        return False
    if outbound.institution.casefold() == inbound.institution.casefold():
        return False
    if outbound.currency != inbound.currency or outbound.instrument_id != inbound.instrument_id:
        return False
    if abs(outbound.occurred_at - inbound.occurred_at) > date_window:
        return False
    if outbound.amount is None or inbound.amount is None:
        return False
    if abs(outbound.amount - inbound.amount) > amount_tolerance:
        return False
    if outbound.quantity is None or inbound.quantity is None:
        return outbound.quantity is None and inbound.quantity is None
    return abs(outbound.quantity - inbound.quantity) <= quantity_tolerance


def reconcile_transfers(
    transactions: Iterable[Transaction],
    *,
    date_window_days: int = 3,
    amount_tolerance: Decimal = Decimal("0.01"),
    quantity_tolerance: Decimal = Decimal("0"),
) -> TransferReconciliation:
    """Encontra pares explícitos e sugere pares sem transfer_id, sem alterar o ledger.

    Uma sugestão só é considerada segura quando cada ponta possui exatamente
    uma candidata e a relação é recíproca. Casos ambíguos exigem confirmação humana.
    """
    if date_window_days < 0 or amount_tolerance < 0 or quantity_tolerance < 0:
        raise ValueError("Tolerâncias não podem ser negativas.")

    events = [
        tx for tx in transactions
        if tx.transaction_type in {TransactionType.TRANSFER_IN, TransactionType.TRANSFER_OUT}
    ]
    linked: dict[str, list[Transaction]] = {}
    unlinked: list[Transaction] = []
    for event in events:
        if event.transfer_id:
            linked.setdefault(event.transfer_id, []).append(event)
        else:
            unlinked.append(event)

    confirmed: list[TransferPair] = []
    incomplete: list[str] = []
    invalid: list[str] = []
    for transfer_id, group in linked.items():
        outs = [tx for tx in group if tx.transaction_type == TransactionType.TRANSFER_OUT]
        ins = [tx for tx in group if tx.transaction_type == TransactionType.TRANSFER_IN]
        if len(outs) == 1 and len(ins) == 1:
            out, incoming = outs[0], ins[0]
            if _economically_compatible(
                out, incoming, amount_tolerance=amount_tolerance,
                quantity_tolerance=quantity_tolerance,
                date_window=timedelta(days=date_window_days),
            ):
                confirmed.append(TransferPair(
                    out.id, incoming.id, abs(out.occurred_at - incoming.occurred_at),
                    abs((out.amount or Decimal("0")) - (incoming.amount or Decimal("0"))),
                ))
            else:
                invalid.append(transfer_id)
        elif len(outs) + len(ins) < 2:
            incomplete.append(transfer_id)
        else:
            invalid.append(transfer_id)

    date_window = timedelta(days=date_window_days)
    candidates: dict[str, list[TransferPair]] = {tx.id: [] for tx in unlinked}
    for outbound in unlinked:
        if outbound.transaction_type != TransactionType.TRANSFER_OUT:
            continue
        for inbound in unlinked:
            if _economically_compatible(
                outbound, inbound, amount_tolerance=amount_tolerance,
                quantity_tolerance=quantity_tolerance, date_window=date_window,
            ):
                pair = TransferPair(
                    outbound.id, inbound.id,
                    abs(outbound.occurred_at - inbound.occurred_at),
                    abs((outbound.amount or Decimal("0")) - (inbound.amount or Decimal("0"))),
                )
                candidates[outbound.id].append(pair)
                candidates[inbound.id].append(pair)

    suggested: list[TransferPair] = []
    ambiguous: set[str] = set()
    matched: set[str] = set()
    for event_id, pairs in candidates.items():
        if len(pairs) > 1:
            ambiguous.add(event_id)
            for pair in pairs:
                ambiguous.add(
                    pair.transfer_in_id if event_id == pair.transfer_out_id else pair.transfer_out_id
                )
    for pair in (p for pairs in candidates.values() for p in pairs):
        if pair in suggested:
            continue
        if pair.transfer_out_id in ambiguous or pair.transfer_in_id in ambiguous:
            continue
        if len(candidates[pair.transfer_out_id]) == 1 and len(candidates[pair.transfer_in_id]) == 1:
            suggested.append(pair)
            matched.update((pair.transfer_out_id, pair.transfer_in_id))

    unmatched = {
        tx.id for tx in unlinked
        if not candidates[tx.id]
    }
    return TransferReconciliation(
        confirmed_pairs=tuple(confirmed),
        suggested_pairs=tuple(sorted(suggested, key=lambda p: (p.transfer_out_id, p.transfer_in_id))),
        ambiguous_transaction_ids=tuple(sorted(ambiguous)),
        unmatched_transaction_ids=tuple(sorted(unmatched)),
        incomplete_transfer_ids=tuple(sorted(incomplete)),
        invalid_transfer_ids=tuple(sorted(invalid)),
    )
