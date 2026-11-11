"""Portfolio Fit: exposições, concentração e cobertura de dados.

O objetivo é descrever a carteira sem inventar atributos ausentes. Look-through
de ETFs, duration de renda fixa e classificação setorial dependem de dados que
o snapshot não carrega; nesses casos a limitação é explícita.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class FitInput:
    name: str
    institution: str
    asset_class: str
    currency: str
    value_brl: float
    liquidity: str | None = None
    risk_category: str | None = None
    ticker: str | None = None


@dataclass(frozen=True)
class ExposureSlice:
    name: str
    value: float
    share: float
    positions: int


@dataclass(frozen=True)
class FitPosition:
    name: str
    institution: str
    asset_class: str
    currency: str
    value_brl: float
    share: float
    liquidity: str | None
    risk_category: str | None


@dataclass(frozen=True)
class CorrelationPair:
    left: str
    right: str
    correlation: float
    observations: int


@dataclass(frozen=True)
class PortfolioFit:
    total_brl: float
    positions: int
    by_class: tuple[ExposureSlice, ...]
    by_institution: tuple[ExposureSlice, ...]
    by_currency: tuple[ExposureSlice, ...]
    top_positions: tuple[FitPosition, ...]
    herfindahl: float | None
    liquidity_coverage: float | None
    credit_coverage: float | None
    correlations: tuple[CorrelationPair, ...]
    unavailable: tuple[str, ...]


def _exposure(
    positions: Sequence[FitInput], total: float, attribute: str
) -> tuple[ExposureSlice, ...]:
    grouped: dict[str, list[float]] = {}
    for position in positions:
        grouped.setdefault(getattr(position, attribute), []).append(position.value_brl)
    slices = [
        ExposureSlice(
            name=name,
            value=math.fsum(values),
            share=math.fsum(values) / total if total > 0 else 0.0,
            positions=len(values),
        )
        for name, values in grouped.items()
    ]
    slices.sort(key=lambda item: item.value, reverse=True)
    return tuple(slices)


def build_fit(
    inputs: Sequence[FitInput],
    *,
    correlations: Sequence[CorrelationPair] = (),
) -> PortfolioFit:
    valid = [
        item
        for item in inputs
        if math.isfinite(item.value_brl) and item.value_brl > 0
    ]
    total = math.fsum(item.value_brl for item in valid)
    if not valid or total <= 0:
        return PortfolioFit(
            total_brl=0.0,
            positions=0,
            by_class=(),
            by_institution=(),
            by_currency=(),
            top_positions=(),
            herfindahl=None,
            liquidity_coverage=None,
            credit_coverage=None,
            correlations=tuple(correlations),
            unavailable=("Sem posições com valor consolidado em BRL.",),
        )

    shares = [item.value_brl / total for item in valid]
    herfindahl = math.fsum(share * share for share in shares)
    liquidity_known = math.fsum(
        item.value_brl for item in valid if item.liquidity
    )
    credit_known = math.fsum(
        item.value_brl for item in valid if item.risk_category
    )

    top = sorted(valid, key=lambda item: item.value_brl, reverse=True)[:5]
    top_positions = tuple(
        FitPosition(
            name=item.name,
            institution=item.institution,
            asset_class=item.asset_class,
            currency=item.currency,
            value_brl=item.value_brl,
            share=item.value_brl / total,
            liquidity=item.liquidity,
            risk_category=item.risk_category,
        )
        for item in top
    )

    unavailable: list[str] = []
    if any(item.asset_class == "etf" for item in valid):
        unavailable.append("Look-through de ETFs indisponível: composição não foi importada.")
    if any(item.asset_class in {"renda_fixa", "credito_privado_coletivo"} for item in valid):
        unavailable.append("Duration e sensibilidade a juros indisponíveis sem fluxos de caixa detalhados.")
    unavailable.append("Classificação setorial indisponível: snapshot não carrega setor.")

    return PortfolioFit(
        total_brl=total,
        positions=len(valid),
        by_class=_exposure(valid, total, "asset_class"),
        by_institution=_exposure(valid, total, "institution"),
        by_currency=_exposure(valid, total, "currency"),
        top_positions=top_positions,
        herfindahl=herfindahl,
        liquidity_coverage=liquidity_known / total,
        credit_coverage=credit_known / total,
        correlations=tuple(correlations),
        unavailable=tuple(unavailable),
    )
