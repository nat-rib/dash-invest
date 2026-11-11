"""Valuation determinístico: DCF com premissas explícitas."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class DcfProjection:
    year: int
    cash_flow: float
    present_value: float


@dataclass(frozen=True)
class DcfResult:
    present_value_explicit: float
    present_value_terminal: float
    enterprise_value: float
    projections: tuple[DcfProjection, ...]


def discounted_cash_flow(
    *,
    base_cash_flow: float,
    growth_rate: float,
    years: int,
    terminal_growth: float,
    discount_rate: float,
) -> DcfResult:
    """Fluxo de caixa livre descontado com valor terminal de Gordon.

    Premissas são explícitas e validadas: a taxa de desconto precisa ser maior
    que o crescimento na perpetuidade. Nenhum valor é inferido.
    """
    values = (base_cash_flow, growth_rate, terminal_growth, discount_rate)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Premissas precisam ser finitas.")
    if base_cash_flow <= 0:
        raise ValueError("Fluxo de caixa base deve ser positivo.")
    if not 1 <= years <= 50:
        raise ValueError("Horizonte deve estar entre 1 e 50 anos.")
    if growth_rate <= -1 or terminal_growth <= -1 or discount_rate <= -1:
        raise ValueError("Taxas devem ser maiores que -100%.")
    if discount_rate <= terminal_growth:
        raise ValueError("Taxa de desconto deve ser maior que o crescimento na perpetuidade.")

    projections: list[DcfProjection] = []
    present_explicit = 0.0
    cash_flow = base_cash_flow
    for year in range(1, years + 1):
        cash_flow *= 1 + growth_rate
        present = cash_flow / (1 + discount_rate) ** year
        present_explicit += present
        projections.append(DcfProjection(year=year, cash_flow=cash_flow, present_value=present))

    terminal = cash_flow * (1 + terminal_growth) / (discount_rate - terminal_growth)
    present_terminal = terminal / (1 + discount_rate) ** years

    return DcfResult(
        present_value_explicit=present_explicit,
        present_value_terminal=present_terminal,
        enterprise_value=present_explicit + present_terminal,
        projections=tuple(projections),
    )
