"""Métricas de rentabilidade com fluxos externos explícitos.

TWR usa períodos delimitados por avaliações feitas imediatamente após os fluxos
externos do período. XIRR usa fluxos sob a ótica do investidor e valor terminal.
Transferências entre instituições nunca são fluxos externos.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from math import isfinite
from typing import Iterable, Sequence

from src.domain.models import Transaction, TransactionType


@dataclass(frozen=True)
class TwrPeriod:
    start_date: date
    end_date: date
    start_value: Decimal
    end_value_after_flows: Decimal
    net_external_flow: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.end_date <= self.start_date:
            raise ValueError("O fim do período deve ser posterior ao início.")
        if self.start_value <= 0:
            raise ValueError("O valor inicial do período deve ser positivo.")
        if self.end_value_after_flows < 0:
            raise ValueError("O valor final não pode ser negativo.")


@dataclass(frozen=True)
class DatedCashFlow:
    date: date
    amount: Decimal  # Ótica do investidor: aporte negativo, retirada positiva.


@dataclass(frozen=True)
class PerformanceResult:
    rate: Decimal
    periods: int
    start_date: date
    end_date: date


def external_cash_flows(transactions: Iterable[Transaction]) -> tuple[DatedCashFlow, ...]:
    """Converte somente aportes/retiradas em fluxos externos do investidor."""
    flows: list[DatedCashFlow] = []
    for tx in transactions:
        if tx.transaction_type == TransactionType.DEPOSIT:
            assert tx.amount is not None
            flows.append(DatedCashFlow(tx.occurred_at.date(), -tx.amount))
        elif tx.transaction_type == TransactionType.WITHDRAWAL:
            assert tx.amount is not None
            flows.append(DatedCashFlow(tx.occurred_at.date(), tx.amount))
        # Transferências internas, proventos, juros, impostos e taxas não são
        # fluxos externos do investidor para a carteira consolidada.
    return tuple(sorted(flows, key=lambda flow: flow.date))


def calculate_twr(periods: Sequence[TwrPeriod]) -> PerformanceResult:
    """Calcula retorno acumulado TWR encadeando subperíodos sem efeito dos aportes.

    end_value_after_flows deve ser a avaliação imediatamente após o fluxo
    externo ocorrido no fim do período. net_external_flow é positivo para
    aportes na carteira e negativo para retiradas.
    """
    if not periods:
        raise ValueError("TWR requer ao menos um período avaliado.")
    ordered = sorted(periods, key=lambda item: (item.start_date, item.end_date))
    growth = Decimal("1")
    previous_end: date | None = None
    for period in ordered:
        if previous_end is not None and period.start_date != previous_end:
            raise ValueError("Os períodos TWR precisam ser contíguos e não sobrepostos.")
        value_before_flow = period.end_value_after_flows - period.net_external_flow
        if value_before_flow < 0:
            raise ValueError("Fluxos externos excedem o valor final observado.")
        growth *= value_before_flow / period.start_value
        previous_end = period.end_date
    return PerformanceResult(
        rate=growth - Decimal("1"),
        periods=len(ordered),
        start_date=ordered[0].start_date,
        end_date=ordered[-1].end_date,
    )


def _npv(rate: float, flows: Sequence[tuple[date, float]]) -> float:
    origin = flows[0][0]
    return sum(amount / ((1.0 + rate) ** ((when - origin).days / 365.0)) for when, amount in flows)


def calculate_xirr(
    cash_flows: Iterable[DatedCashFlow],
    *,
    terminal_value: Decimal,
    terminal_date: date,
    tolerance: float = 1e-10,
    max_iterations: int = 300,
) -> Decimal:
    """Resolve XIRR por bisseção, com datas reais e base anual de 365 dias.

    cash_flows usam a ótica do investidor (aportes negativos, retiradas positivas).
    terminal_value é o patrimônio final positivo na mesma moeda.
    """
    if terminal_value < 0:
        raise ValueError("O valor terminal não pode ser negativo.")
    flows = list(cash_flows)
    flows.append(DatedCashFlow(terminal_date, terminal_value))
    if not flows:
        raise ValueError("XIRR requer fluxos.")
    if any(not amount.is_finite() for amount in (flow.amount for flow in flows)):
        raise ValueError("Todos os fluxos devem ser finitos.")
    if any(flow.date > terminal_date for flow in flows):
        raise ValueError("Há fluxo posterior à data terminal.")
    flows.sort(key=lambda item: item.date)
    if len({flow.date for flow in flows}) < 2:
        raise ValueError("XIRR requer ao menos duas datas distintas.")
    amounts = [flow.amount for flow in flows]
    if not any(amount < 0 for amount in amounts) or not any(amount > 0 for amount in amounts):
        raise ValueError("XIRR requer ao menos um fluxo positivo e um negativo.")

    numeric = [(flow.date, float(flow.amount)) for flow in flows]
    # XIRR pode ter mais de uma raiz quando há múltiplas mudanças de sinal.
    # Procuramos brackets em uma malha ampla e recusamos soluções ambíguas.
    grid = [-0.9999, -0.99, -0.9, -0.75, -0.5, -0.25, 0.0, 0.1, 0.25, 0.5,
            1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 500.0, 1000.0]
    brackets: list[tuple[float, float]] = []
    previous_rate = grid[0]
    previous_npv = _npv(previous_rate, numeric)
    for rate in grid[1:]:
        current_npv = _npv(rate, numeric)
        if previous_npv == 0:
            brackets.append((previous_rate, previous_rate))
        elif current_npv == 0 or (previous_npv < 0 < current_npv) or (current_npv < 0 < previous_npv):
            brackets.append((previous_rate, rate))
        previous_rate, previous_npv = rate, current_npv
    if not brackets:
        raise ValueError("Não foi possível encontrar uma taxa XIRR no intervalo suportado.")
    if len(brackets) > 1:
        raise ValueError("Os fluxos admitem múltiplas raízes XIRR; resultado ambíguo.")

    low, high = brackets[0]
    if low == high:
        root = low
    else:
        low_npv = _npv(low, numeric)
        root = (low + high) / 2
        for _ in range(max_iterations):
            root = (low + high) / 2
            value = _npv(root, numeric)
            if abs(value) <= tolerance or abs(high - low) <= tolerance:
                break
            if (low_npv < 0 and value > 0) or (low_npv > 0 and value < 0):
                high = root
            else:
                low, low_npv = root, value
        else:
            raise ArithmeticError("XIRR não convergiu dentro do limite de iterações.")
    if not isfinite(root):
        raise ArithmeticError("XIRR resultou em taxa não finita.")
    return Decimal(str(root))
