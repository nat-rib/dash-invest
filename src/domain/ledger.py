"""Reconstrução determinística de posição a partir do ledger.

A função trabalha em uma instituição por vez. Transferências entre instituições
são representadas por eventos pareados (TRANSFER_OUT / TRANSFER_IN), sem aporte
ou retirada externa. Valores de transferência de ativo representam custo
contábil transferido, não valor de mercado.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from src.domain.models import PortfolioPosition, Transaction, TransactionType


class InsufficientPositionError(ValueError):
    """Uma saída excede a quantidade disponível na instituição."""


class IncompleteOpeningPositionError(ValueError):
    """Snapshot de abertura sem quantidade não pode ser tratado como posição zero."""


@dataclass(frozen=True)
class PositionReconstruction:
    position: PortfolioPosition
    cost_basis: Decimal | None
    realized_profit: Decimal | None
    transactions_applied: int


def _trade_amount(transaction: Transaction) -> Decimal:
    if transaction.amount is not None:
        return transaction.amount
    if transaction.quantity is None or transaction.unit_price is None:
        raise ValueError("Operação precisa de amount ou quantity × unit_price.")
    return transaction.quantity * transaction.unit_price


def rebuild_position(
    *, portfolio_id: str,
    instrument_id: str,
    institution: str,
    transactions: Iterable[Transaction],
    opening_position: PortfolioPosition | None = None,
) -> PositionReconstruction:
    """Reconstrói quantidade, custo médio e lucro realizado para um ativo/local.

    BUY incorpora custos e impostos ao custo. SELL reduz custo pelo custo médio
    e calcula resultado realizado líquido de taxas/impostos. SPLIT usa
    metadata.ratio; BONUS adiciona unidades sem alterar o custo total.
    AMORTIZATION reduz o custo contábil. Dividendos e juros não alteram unidades.
    """
    if opening_position is not None:
        expected = (portfolio_id, instrument_id, institution)
        actual = (
            opening_position.portfolio_id,
            opening_position.instrument_id,
            opening_position.institution,
        )
        if actual != expected:
            raise ValueError("A posição de abertura não corresponde ao ativo/carteira/instituição.")
        if opening_position.quantity is None:
            raise IncompleteOpeningPositionError(
                "A posição de abertura não informa quantidade; não é seguro assumir zero."
            )
        quantity = opening_position.quantity
        if quantity == 0:
            cost_basis: Decimal | None = Decimal("0")
        elif opening_position.average_cost is None:
            cost_basis = None
        else:
            cost_basis = quantity * opening_position.average_cost
        currency = opening_position.cost_currency
        metadata = dict(opening_position.metadata)
        as_of = opening_position.as_of
    else:
        quantity = Decimal("0")
        cost_basis = Decimal("0")
        currency = None
        metadata = {}
        as_of = None

    ordered = sorted(transactions, key=lambda tx: (tx.occurred_at, tx.sequence, tx.id))
    realized_profit: Decimal | None = Decimal("0") if cost_basis is not None else None

    for tx in ordered:
        if opening_position is not None and tx.occurred_at.date() <= opening_position.as_of:
            raise ValueError("Transações devem ocorrer após a data do snapshot de abertura.")
        if (tx.portfolio_id, tx.instrument_id, tx.institution) != (
            portfolio_id, instrument_id, institution
        ):
            raise ValueError("Ledger contém transação de outra carteira, ativo ou instituição.")
        if currency is None:
            currency = tx.currency
        elif tx.currency != currency:
            raise ValueError(
                "Transações em moedas diferentes exigem conversão cambial explícita antes da reconstrução."
            )
        as_of = tx.occurred_at.date()

        if tx.transaction_type == TransactionType.BUY:
            assert tx.quantity is not None
            quantity += tx.quantity
            if cost_basis is not None:
                cost_basis += _trade_amount(tx) + tx.fees + tx.taxes

        elif tx.transaction_type == TransactionType.SELL:
            assert tx.quantity is not None
            if tx.quantity > quantity:
                raise InsufficientPositionError(
                    f"Venda de {tx.quantity} excede saldo de {quantity} em {institution}."
                )
            if cost_basis is not None and quantity > 0:
                basis_removed = cost_basis if tx.quantity == quantity else (cost_basis / quantity) * tx.quantity
                net_proceeds = _trade_amount(tx) - tx.fees - tx.taxes
                realized_profit = (realized_profit or Decimal("0")) + net_proceeds - basis_removed
                cost_basis -= basis_removed
            else:
                realized_profit = None
            quantity -= tx.quantity
            if quantity == 0:
                cost_basis = Decimal("0")

        elif tx.transaction_type == TransactionType.TRANSFER_OUT:
            assert tx.quantity is not None and tx.amount is not None
            if tx.quantity > quantity:
                raise InsufficientPositionError(
                    f"Transferência de saída de {tx.quantity} excede saldo de {quantity} em {institution}."
                )
            if cost_basis is not None:
                if tx.amount > cost_basis:
                    raise ValueError("Custo transferido supera o custo contábil disponível.")
                cost_basis -= tx.amount
            quantity -= tx.quantity
            if quantity == 0:
                if cost_basis is not None and cost_basis != 0:
                    raise ValueError("Transferência total deve carregar todo o custo contábil remanescente.")
                cost_basis = Decimal("0")

        elif tx.transaction_type == TransactionType.TRANSFER_IN:
            assert tx.quantity is not None and tx.amount is not None
            quantity += tx.quantity
            if cost_basis is not None:
                cost_basis += tx.amount

        elif tx.transaction_type == TransactionType.BONUS:
            assert tx.quantity is not None
            quantity += tx.quantity

        elif tx.transaction_type == TransactionType.SPLIT:
            ratio = Decimal(str(tx.metadata["ratio"]))
            quantity *= ratio

        elif tx.transaction_type == TransactionType.AMORTIZATION:
            assert tx.amount is not None
            if cost_basis is not None:
                if tx.amount > cost_basis:
                    raise ValueError("Amortização supera o custo contábil disponível.")
                cost_basis -= tx.amount

        # Proventos, juros, cupons, depósitos, retiradas, impostos e taxas
        # não alteram quantidade/custo da posição nesta projeção.

    if currency is None or as_of is None:
        raise ValueError("Informe uma posição de abertura ou ao menos uma transação para definir moeda/data.")
    average_cost = (cost_basis / quantity) if cost_basis is not None and quantity > 0 else None
    position = PortfolioPosition(
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        institution=institution,
        quantity=quantity,
        average_cost=average_cost,
        cost_currency=currency,
        as_of=as_of,
        metadata=metadata,
    )
    return PositionReconstruction(
        position=position,
        cost_basis=cost_basis,
        realized_profit=realized_profit,
        transactions_applied=len(ordered),
    )
